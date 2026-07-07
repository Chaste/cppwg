"""Wrapper code writer for C++ free functions."""

from typing import TYPE_CHECKING

from cppwg.info.free_function_info import CppFreeFunctionInfo
from cppwg.utils import utils
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
        default_args = ""
        if not self.free_function_info.hierarchy_attribute("exclude_default_args"):
            for arg in self.free_function_info.decls[0].arguments:
                default_args += f', py::arg("{arg.name}")'
                if arg.default_value is not None:
                    # Try to convert "(-1)" to "-1" etc.
                    default_value = str(arg.default_value)
                    value = utils.str_to_num(
                        default_value, integer="int" in str(arg.decl_type)
                    )
                    if value is not None:
                        default_value = str(value)
                    default_args += f" = {default_value}"

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
        info = self.free_function_info
        decl = info.decls[0]

        # Exclude by return type. return_type_excludes targets return types; the
        # deprecated calldef_excludes applies to both return and arg types.
        calldef_excludes = info.hierarchy_attribute_gather_flat("calldef_excludes")
        return_type_excludes = (
            info.hierarchy_attribute_gather_flat("return_type_excludes")
            + calldef_excludes
        )
        return_type = decl.return_type.decl_string
        if any(
            utils.type_string_matches(return_type, pattern)
            for pattern in return_type_excludes
        ):
            return True

        # Exclude by argument type. arg_type_excludes is the general arg-type
        # exclude; the deprecated calldef_excludes applies too.
        arg_type_excludes = (
            info.hierarchy_attribute_gather_flat("arg_type_excludes") + calldef_excludes
        )
        for argument_type in decl.argument_types:
            arg_type = argument_type.decl_string
            if any(
                utils.type_string_matches(arg_type, pattern)
                for pattern in arg_type_excludes
            ):
                return True

        return False
