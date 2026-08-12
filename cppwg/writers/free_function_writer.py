"""Wrapper code writer for C++ free functions."""

from typing import TYPE_CHECKING

from cppwg.info import exclusions
from cppwg.info.free_function_info import CppFreeFunctionInfo
from cppwg.writers.base_writer import CppBaseWrapperWriter

if TYPE_CHECKING:
    from string import Template


class CppFreeFunctionWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of free function wrapper code.

    Attributes
    ----------
    free_function_info : CppFreeFunctionInfo
        The free function information to generate Python bindings for
    wrapper_templates : dict[str, Template]
        Templates with placeholders for generating wrapper code
    """

    def __init__(self, free_function_info, wrapper_templates) -> None:
        super().__init__(wrapper_templates)

        self.free_function_info: CppFreeFunctionInfo = free_function_info
        self.wrapper_templates: dict[str, "Template"] = wrapper_templates

    def generate_wrapper(self) -> str:
        """
        Generate the free function wrapper code.

        Returns
        -------
        str
            The updated C++ wrapper code string
        """
        # Skip this free function if it uses any excluded arg types or return types
        if self.exclude():
            return ""

        # Pybind11 def type e.g. "_static" for def_static()
        def_adorn = ""

        # Pybind11 arg string with or without default values.
        # e.g. without default values: ', py::arg("foo"), py::arg("bar")'
        # e.g. with default values: ', py::arg("foo") = 1, py::arg("bar") = 2'
        # exclude_default_args omits the values but keeps the py::arg names.
        default_args = self.render_default_args(
            self.free_function_info.decls[0].arguments,
            self.free_function_info.hierarchy_attribute("exclude_default_args"),
        )

        # Add the free function wrapper code to the wrapper string
        func_dict = {
            "def_adorn": def_adorn,
            "function_name": self.free_function_info.decls[0].name,
            "function_docs": '" "',
            "default_args": default_args,
        }
        wrapper_string = self.wrapper_templates["free_function"].substitute(**func_dict)

        return wrapper_string

    def exclude(self) -> bool:
        """
        Check if the function should be excluded from the wrapper code.

        Returns
        -------
        bool
            True if the function should be excluded from wrapper code, False otherwise.
        """
        # Config-excluded (YAML `excluded: true`) or dropped for an excluded
        # arg/return type. The type-based rule lives in free_function_is_excluded,
        # shared with the package model; the config flag is folded in here (as the
        # enum writer does with enum_info.excluded) so the writer and model agree
        # on the wrapped set.
        return (
            self.free_function_info.excluded
            or exclusions.free_function_is_excluded(self.free_function_info)
        )
