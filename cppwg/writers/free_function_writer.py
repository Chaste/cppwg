"""Wrapper code writer for C++ free functions."""

from typing import Dict, List

from cppwg.input.free_function_info import CppFreeFunctionInfo
from cppwg.writers.base_writer import CppBaseWrapperWriter


class CppFreeFunctionWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of free function wrapper code.

    Attributes
    ----------
    free_function_info : CppFreeFunctionInfo
        The free function information to generate Python bindings for
    wrapper_templates : Dict[str, str]
        String templates with placeholders for generating wrapper code
    exclusion_args : List[str]
        A list of argument types to exclude from the wrapper code
    """

    def __init__(self, free_function_info, wrapper_templates) -> None:

        super(CppFreeFunctionWrapperWriter, self).__init__(wrapper_templates)

        self.free_function_info: CppFreeFunctionInfo = free_function_info
        self.wrapper_templates: Dict[str, str] = wrapper_templates
        self.exclusion_args: List[str] = []

    def add_self(self, wrapper_string) -> str:
        """
        Add the free function wrapper code to the wrapper code string.

        Parameters
        ----------
        wrapper_string : str
            String containing the current C++ wrapper code

        Returns
        -------
        str
            The updated C++ wrapper code string
        """
        # Skip this free function if it uses any excluded arg types or return types
        if self.exclusion_criteria(self.free_function_info.decl, self.exclusion_args):
            return wrapper_string

        # Pybind11 def type e.g. "_static" for def_static()
        def_adorn = ""

        # Pybind11 arg string with or without default values.
        # e.g. without default values: ', py::arg("foo"), py::arg("bar")'
        # e.g. with default values: ', py::arg("foo") = 1, py::arg("bar") = 2'
        default_args = ""
        if not self.default_arg_exclusion_criteria():
            for argument in self.free_function_info.decl.arguments:
                default_args += f', py::arg("{argument.name}")'
                if argument.default_value is not None:
                    default_args += f" = {argument.default_value}"

        # Add the free function wrapper code to the wrapper string
        func_dict = {
            "def_adorn": def_adorn,
            "function_name": self.free_function_info.decl.name,
            "function_docs": '" "',
            "default_args": default_args,
        }
        wrapper_string += self.wrapper_templates["free_function"].format(**func_dict)

        return wrapper_string
