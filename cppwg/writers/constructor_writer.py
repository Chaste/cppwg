"""Wrapper code writer for C++ class constructors."""

from typing import TYPE_CHECKING

from cppwg.info import exclusions
from cppwg.writers.base_writer import CppBaseWrapperWriter

if TYPE_CHECKING:
    from string import Template

    from pygccxml.declarations.calldef_members import constructor_t
    from pygccxml.declarations.class_declaration import class_t

    from cppwg.info.class_info import CppClassInfo


class CppConstructorWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of constructor wrapper code.

    Attributes
    ----------
    class_info : CppClassInfo
        The class information for the class containing the constructor
    template_idx: int
        The index of the template in class_info
    ctor_decl : pygccxml.declarations.constructor_t
        The pygccxml declaration object for the constructor
    class_decl : pygccxml.declarations.class_t
        The class declaration for the class containing the constructor
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
        ctor_decl: "constructor_t",
        wrapper_templates: dict[str, "Template"],
    ) -> None:
        super().__init__(wrapper_templates)

        self.class_info: "CppClassInfo" = class_info
        self.ctor_decl: "constructor_t" = ctor_decl
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
        Check if the constructor should be excluded from the wrapper code.

        Returns
        -------
        bool
            True if the constructor should be excluded, False otherwise
        """
        return exclusions.constructor_is_excluded(
            self.class_info, self.class_decl, self.ctor_decl
        )

    def generate_wrapper(self) -> str:
        """
        Generate the constructor wrapper code.

        Example output:
        .def(py::init<int, bool >(), py::arg("i") = 1, py::arg("b") = false)

        Returns
        -------
        str
            The constructor wrapper code.
        """
        # Skip excluded constructors
        if self.exclude():
            return ""

        # Get the arg signature e.g. "int, bool"
        arg_types = [t.decl_string for t in self.ctor_decl.argument_types]
        arg_signature = ", ".join(arg_types)

        # Keyword args with default values e.g. py::arg("i") = 1. Empty
        # initializer-list defaults ({}) are given their type (constructor-only).
        keyword_args = self.render_default_args(
            self.ctor_decl.arguments,
            self.class_info.hierarchy_attribute("exclude_default_args"),
            template_params=self.template_params,
            template_args=self.template_args,
            class_name=self.class_info.name,
            substitute_empty_init_list=True,
        )

        ctor_dict = {
            "arg_signature": arg_signature,
            "default_args": keyword_args,
        }
        class_constructor_template = self.wrapper_templates["class_constructor"]
        wrapper_string = class_constructor_template.substitute(**ctor_dict)

        return wrapper_string
