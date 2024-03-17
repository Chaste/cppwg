from typing import Optional

from pygccxml import declarations
from pygccxml.declarations.class_declaration import class_t
from pygccxml.declarations.calldef_members import member_function_t

from cppwg.input.class_info import CppClassInfo
from cppwg.writers.base_writer import CppBaseWrapperWriter


class CppMethodWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of method wrapper code

    Attributes
    ----------
    class_info : ClassInfo
        The class information for the class containing the method
    method_decl : member_function_t
        The pygccxml declaration object for the method
    class_decl : class_t
        The class declaration for the class containing the method
    wrapper_templates : dict[str, str]
        String templates with placeholders for generating wrapper code
    class_short_name : Optional[str]
        The short name of the class e.g. 'Foo2_2'
    """

    def __init__(
        self,
        class_info: CppClassInfo,
        method_decl: member_function_t,
        class_decl: class_t,
        wrapper_templates: dict[str, str],
        class_short_name: Optional[str] = None,
    ):

        super(CppMethodWrapperWriter, self).__init__(wrapper_templates)

        self.class_info: CppClassInfo = class_info
        self.method_decl: member_function_t = method_decl
        self.class_decl: class_t = class_decl

        self.class_short_name: str = class_short_name
        if self.class_short_name is None:
            self.class_short_name = self.class_decl.name

    def exclusion_criteria(self) -> bool:
        """
        Check if the method should be excluded from the wrapper code

        Returns
        -------
        bool
            True if the method should be excluded, False otherwise
        """

        # Exclude private methods without over-rides
        if self.method_decl.access_type == "private":
            return True

        # Exclude sub class (e.g. iterator) methods such as:
        #   class Foo {
        #     public:
        #       class FooIterator {
        if self.method_decl.parent != self.class_decl:
            return True

        # Check for excluded return types
        calldef_excludes = [
            x.replace(" ", "")
            for x in self.class_info.hierarchy_attribute_gather("calldef_excludes")
        ]

        return_type_excludes = [
            x.replace(" ", "")
            for x in self.class_info.hierarchy_attribute_gather("return_type_excludes")
        ]

        return_type = self.method_decl.return_type.decl_string.replace(" ", "")
        if return_type in calldef_excludes or return_type in return_type_excludes:
            return True

        # Check for excluded argument patterns
        for argument_type in self.method_decl.argument_types:
            # e.g. ::std::vector<unsigned int> const & -> ::std::vector<unsigned
            arg_type_short = argument_type.decl_string.split()[0].replace(" ", "")
            if arg_type_short in calldef_excludes:
                return True

            # e.g. ::std::vector<unsigned int> const & -> ::std::vector<unsignedint>const&
            arg_type_full = argument_type.decl_string.replace(" ", "")
            if arg_type_full in calldef_excludes:
                return True

        return False

    def add_self(self, cpp_string) -> str:
        """
        Add the method wrapper code to the input string. For example:
        .def("bar", (void(Foo::*)(double)) &Foo::bar, " ", py::arg("d") = 1.0)

        Parameters
        ----------
        cpp_string : str
            The input string containing current wrapper code

        Returns
        -------
        str
            The input string with the method wrapper code added
        """

        # Skip excluded methods
        if self.exclusion_criteria():
            return cpp_string

        # Pybind11 def type e.g. "_static" for def_static()
        def_adorn = ""
        if self.method_decl.has_static:
            def_adorn += "_static"

        # How to point to class
        if self.method_decl.has_static:
            self_ptr = "*"
        else:
            # e.g. Foo2_2::*
            self_ptr = self.class_short_name + "::*"

        # Const-ness
        const_adorn = ""
        if self.method_decl.has_const:
            const_adorn = " const "

        # Get the arg signature e.g. "int, bool"
        arg_types = [t.decl_string for t in self.method_decl.argument_types]
        arg_signature = ", ".join(arg_types)

        # Default args e.g. py::arg("d") = 1.0
        default_args = ""
        if not self.default_arg_exclusion_criteria():
            for arg, arg_type in zip(
                self.method_decl.arguments, self.method_decl.argument_types
            ):
                default_args += f', py::arg("{arg.name}")'

                if arg.default_value is not None:
                    default_value = str(arg.default_value)

                    # Hack for missing template in default args
                    # e.g. Foo<2>::bar(Bar<2> const & b = Bar<DIM>())
                    # TODO: Make more robust
                    arg_type_str = str(arg_type).replace(" ", "")
                    if "<DIM>" in default_value:
                        if "<2>" in arg_type_str:
                            default_value = default_value.replace("<DIM>", "<2>")
                        elif "<3>" in arg_type_str:
                            default_value = default_value.replace("<DIM>", "<3>")

                    default_args += f" = {default_value}"

        # Call policy, e.g. "py::return_value_policy::reference"
        call_policy = ""
        if declarations.is_pointer(self.method_decl.return_type):
            ptr_policy = self.class_info.hierarchy_attribute("pointer_call_policy")
            if ptr_policy:
                call_policy = f", py::return_value_policy::{ptr_policy}"

        elif declarations.is_reference(self.method_decl.return_type):
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
            "class_short_name": self.class_short_name,
            "method_docs": '" "',
            "default_args": default_args,
            "call_policy": call_policy,
        }
        class_method_template = self.wrapper_templates["class_method"]
        cpp_string += class_method_template.format(**method_dict)

        return cpp_string

    def add_override(self, cpp_string) -> str:
        """
        Add overrides for virtual methods to the input string.

        Parameters
        ----------
        cpp_string : str
            The input string containing current wrapper code

        Returns
        -------
        str
            The input string with the virtual override wrapper code added
        """

        # Skip private methods
        if self.method_decl.access_type == "private":
            return cpp_string

        # arg_string = ""
        # num_arg_types = len(self.method_decl.argument_types)
        # args = self.method_decl.arguments
        # for idx, eachArg in enumerate(self.method_decl.argument_types):
        #     arg_string += eachArg.decl_string + " " + args[idx].name
        #     if idx < num_arg_types-1:
        #         arg_string += ", "

        # Get list of arguments and types
        arg_list = []
        arg_name_list = []

        for arg, arg_type in zip(
            self.method_decl.arguments, self.method_decl.argument_types
        ):
            arg_list.append(f"{arg_type.decl_string} {arg.name}")
            arg_name_list.append(f"        {arg.name}")

        arg_string = ", ".join(arg_list)  # e.g. "int a, bool b, double c"
        arg_name_string = ",\n".join(arg_name_list)  # e.g. "a,\n b,\n c"

        # Const-ness
        const_adorn = ""
        if self.method_decl.has_const:
            const_adorn = " const "

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
            "short_class_name": self.class_short_name,
            "args_string": arg_name_string,
        }
        cpp_string += self.wrapper_templates["method_virtual_override"].format(
            **override_dict
        )

        return cpp_string
