"""Wrapper code writer for C++ methods."""

import re
from typing import TYPE_CHECKING

from pygccxml.declarations import type_traits

from cppwg.utils import utils
from cppwg.writers.base_writer import CppBaseWrapperWriter

if TYPE_CHECKING:
    from string import Template

    from pygccxml.declarations.calldef_members import member_function_t
    from pygccxml.declarations.class_declaration import class_t

    from cppwg.info.class_info import CppClassInfo


class CppMethodWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of method wrapper code.

    Attributes
    ----------
    class_info : CppClassInfo
        The class information for the class containing the method
    template_idx: int
        The index of the template in class_info
    method_decl : [pygccxml.declarations.member_function_t]
        The pygccxml declaration object for the method
    class_decl : [pygccxml.declarations.class_t]
        The class declaration for the class containing the method
    wrapper_templates : dict[str, Template]
        Templates with placeholders for generating wrapper code
    class_py_name : str | None
        The Python name of the class e.g. 'Foo_2_2'
    template_params: list[str] | None
        The template params for the class e.g. ['DIM_A', 'DIM_B']
    template_args: list[str] | None
        The template args for the class e.g. ['2', '2']
    """

    def __init__(
        self,
        class_info: "CppClassInfo",
        template_idx: int,
        method_decl: "member_function_t",
        wrapper_templates: dict[str, "Template"],
    ) -> None:
        super().__init__(wrapper_templates)

        self.class_info: "CppClassInfo" = class_info
        self.method_decl: "member_function_t" = method_decl
        self.class_decl: "class_t" = class_info.decls[template_idx]

        self.class_py_name = class_info.py_names[template_idx]
        if self.class_py_name is None:
            self.class_py_name = self.class_decl.name

        self.template_params = class_info.template_params

        self.template_args = None
        if class_info.template_arg_lists:
            self.template_args = class_info.template_arg_lists[template_idx]

    def exclude(self) -> bool:
        """
        Check if the method should be excluded from the wrapper code.

        Returns
        -------
        bool
            True if the method should be excluded, False otherwise
        """
        return self.method_is_excluded(
            self.class_info, self.class_decl, self.method_decl
        )

    @staticmethod
    def method_is_excluded(
        class_info: "CppClassInfo",
        class_decl: "class_t",
        method_decl: "member_function_t",
    ) -> bool:
        """
        Return True if a method would be excluded from the wrapper code.

        The per-instance exclude() delegates here so the same decision can be
        reused without a writer. The inherited-override overload-shadowing guard
        (see class_writer._is_inherited_override) needs it: a sibling overload
        that is excluded emits no binding, so it cannot shadow an inherited base
        overload set and must not block skipping a redundant override.

        Parameters
        ----------
        class_info : CppClassInfo
            The info for the class containing the method.
        class_decl : pygccxml.declarations.class_t
            The declaration of the class the method is being wrapped on.
        method_decl : pygccxml.declarations.member_function_t
            The candidate method.

        Returns
        -------
        bool
            True if the method should be excluded, False otherwise.
        """
        # Skip methods marked for exclusion
        if class_info.excluded_methods:
            if method_decl.name in class_info.excluded_methods:
                return True

        # Exclude private methods
        if method_decl.access_type == "private":
            return True

        # Exclude sub class (e.g. iterator) methods such as:
        #   class Foo {
        #     public:
        #       class FooIterator {
        if method_decl.parent != class_decl:
            return True

        # Exclude by return type. return_type_excludes targets return types;
        # the deprecated calldef_excludes applies to both return and arg types.
        calldef_excludes = class_info.hierarchy_attribute_gather_flat(
            "calldef_excludes"
        )
        return_type_excludes = (
            class_info.hierarchy_attribute_gather_flat("return_type_excludes")
            + calldef_excludes
        )

        return_type = method_decl.return_type.decl_string
        if any(
            utils.type_string_matches(return_type, pattern)
            for pattern in return_type_excludes
        ):
            return True

        # Exclude by argument type. arg_type_excludes targets argument types on
        # methods and constructors; the deprecated calldef_excludes applies too.
        arg_type_excludes = (
            class_info.hierarchy_attribute_gather_flat("arg_type_excludes")
            + calldef_excludes
        )
        for argument_type in method_decl.argument_types:
            arg_type = argument_type.decl_string
            if any(
                utils.type_string_matches(arg_type, pattern)
                for pattern in arg_type_excludes
            ):
                return True

        return False

    def generate_wrapper(self) -> str:
        """
        Generate the method wrapper code.

        Example output:
        .def("bar", (void(Foo::*)(double)) &Foo::bar, " ", py::arg("d") = 1.0)

        Returns
        -------
        str
            The method wrapper code.
        """
        # Skip excluded methods
        if self.exclude():
            return ""

        # Pybind11 def type e.g. "_static" for def_static()
        def_adorn = ""
        if self.method_decl.has_static:
            def_adorn = "_static"

        # How to point to class
        if self.method_decl.has_static:
            self_ptr = "*"
        else:
            # e.g. Foo_2_2::*
            self_ptr = self.class_py_name + "::*"

        # Const-ness
        const_adorn = ""
        if self.method_decl.has_const:
            const_adorn = " const"

        # Get the arg signature e.g. "int, bool"
        arg_types = [t.decl_string for t in self.method_decl.argument_types]
        arg_signature = ", ".join(arg_types)

        # Keyword args with default values e.g. py::arg("i") = 1
        keyword_args = ""
        for arg in self.method_decl.arguments:
            keyword_args += f', py::arg("{arg.name}")'

            if not (
                arg.default_value is None
                or self.class_info.hierarchy_attribute("exclude_default_args")
            ):
                # Try to convert "(-1)" to "-1" etc.
                default_value = str(arg.default_value)
                value = utils.str_to_num(
                    default_value, integer="int" in str(arg.decl_type)
                )
                if value is not None:
                    default_value = str(value)

                # Check for template params in default value
                if self.template_params:
                    for param, val in zip(self.template_params, self.template_args):
                        if param in default_value:
                            # Replace e.g. Foo::DIM_A -> 2
                            default_value = re.sub(
                                f"\\b{self.class_info.name}::{param}\\b",
                                str(val),
                                default_value,
                            )

                            # Replace e.g. <DIM_A> -> <2>
                            default_value = re.sub(
                                f"\\b{param}\\b", f"{val}", default_value
                            )

                keyword_args += f" = {default_value}"

        # Call policy, e.g. "py::return_value_policy::reference"
        call_policy = ""
        if type_traits.is_pointer(self.method_decl.return_type):
            ptr_policy = self.class_info.hierarchy_attribute("pointer_call_policy")
            if ptr_policy:
                call_policy = f", py::return_value_policy::{ptr_policy}"

        elif type_traits.is_reference(self.method_decl.return_type):
            ref_policy = self.class_info.hierarchy_attribute("reference_call_policy")
            if ref_policy:
                call_policy = f", py::return_value_policy::{ref_policy}"

        method_dict = {
            "def_adorn": def_adorn,
            "method_name": self.method_decl.name,
            "return_type": self.method_decl.return_type.decl_string,
            "self_ptr": self_ptr,
            "arg_signature": arg_signature,
            "const_adorn": const_adorn,
            "class_py_name": self.class_py_name,
            "method_docs": '" "',
            "default_args": keyword_args,
            "call_policy": call_policy,
        }
        class_method_template = self.wrapper_templates["class_method"]
        wrapper_string = class_method_template.substitute(**method_dict)

        return wrapper_string

    def generate_virtual_override_wrapper(self) -> str:
        """
        Generate wrapper code for overriding virtual methods.

        Example output:
        ```
        void bar(double d) const override {
            PYBIND11_OVERRIDE_PURE(
                bar,
                Foo_2_2,
                bar,
                d);
        }
        ```

        Returns
        -------
        str
            The virtual override wrapper code.
        """
        # Skip excluded methods
        if self.exclude():
            return ""

        # Get list of arguments and types
        arg_list = []
        arg_name_list = []

        for i, (arg, arg_type) in enumerate(
            zip(self.method_decl.arguments, self.method_decl.argument_types)
        ):
            arg_list.append(f"{arg_type.decl_string} {arg.name}")
            if i == 0:
                arg_name_list.append(f"{arg.name}")
            else:
                arg_name_list.append(" " * 12 + f"{arg.name}")

        arg_string = ", ".join(arg_list)  # e.g. "int a, bool b, double c"
        arg_name_string = ",\n".join(arg_name_list)  # e.g. "a,\n b,\n c"

        # Const-ness
        const_adorn = ""
        if self.method_decl.has_const:
            const_adorn = " const"

        # For pure virtual methods, use PYBIND11_OVERRIDE_PURE
        overload_adorn = ""
        if self.method_decl.virtuality == "pure virtual":
            overload_adorn = "_PURE"

        # Get the return type e.g. "void"
        return_string = self.method_decl.return_type.decl_string

        # Add the override code from the template
        override_dict = {
            "return_type": return_string,
            "method_name": self.method_decl.name,
            "arg_string": arg_string,
            "const_adorn": const_adorn,
            "overload_adorn": overload_adorn,
            "tidy_method_name": self.tidy_name(return_string),
            "class_py_name": self.class_py_name,
            "args_string": arg_name_string,
        }
        wrapper_string = self.wrapper_templates["method_virtual_override"].substitute(
            **override_dict
        )

        return wrapper_string
