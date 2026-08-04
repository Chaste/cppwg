"""Wrapper code writer for C++ enums."""

from typing import TYPE_CHECKING

from cppwg.info.enum_info import CppEnumInfo
from cppwg.writers.base_writer import CppBaseWrapperWriter

if TYPE_CHECKING:
    from string import Template


class CppEnumWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of enum wrapper code.

    A plain (namespace-scope) enum is registered directly against the module,
    unlike the struct-enum special case (see CppClassWrapperWriter) which nests a
    single enum inside a wrapped struct. Both scoped (``enum class``) and unscoped
    enums flow through here: ``.value("V", Enum::V)`` qualifies correctly for
    either. ``.export_values()`` (which exports the enumerators into the enclosing
    scope) is emitted by default only for an unscoped enum; a scoped enum, whose
    enumerators stay on the type, closes the chain with a plain ``;``. The
    ``export_values`` config option overrides this either way
    (see CppEnumInfo.should_export_values).

    Attributes
    ----------
    enum_info : CppEnumInfo
        The enum information to generate Python bindings for
    wrapper_templates : dict[str, Template]
        Templates with placeholders for generating wrapper code
    """

    def __init__(self, enum_info, wrapper_templates) -> None:
        super().__init__(wrapper_templates)

        self.enum_info: CppEnumInfo = enum_info
        self.wrapper_templates: dict[str, "Template"] = wrapper_templates

    def generate_wrapper(self) -> str:
        """
        Generate the enum wrapper code.

        Returns
        -------
        str
            The C++ wrapper code string
        """
        if self.exclude():
            return ""

        enum_decl = self.enum_info.decls[0]
        enum_cpp_name = enum_decl.name
        enum_py_name = self.enum_info.name_override or self.enum_info.name

        # One .value("NAME", Enum::NAME) line per enumerator. enum_decl.values is
        # a list of (name, number) tuples in source order; only the name is used.
        enum_values = "".join(
            f'    .value("{value[0]}", {enum_cpp_name}::{value[0]})\n'
            for value in enum_decl.values
        )

        # .export_values() exports the enumerators into the enclosing (module)
        # scope. By default this mirrors the C++ enum kind (unscoped enums export,
        # scoped ones do not), but the export_values config option can force it
        # either way. When not exported, close the chain with a plain `;`.
        if self.enum_info.should_export_values():
            enum_terminator = "    .export_values();\n"
        else:
            enum_terminator = "    ;\n"

        enum_dict = {
            "enum_cpp_name": enum_cpp_name,
            "enum_py_name": enum_py_name,
            "enum_values": enum_values,
            "enum_terminator": enum_terminator,
        }
        return self.wrapper_templates["enum_register"].substitute(**enum_dict)

    def exclude(self) -> bool:
        """
        Check if the enum should be excluded from the wrapper code.

        Returns
        -------
        bool
            True if the enum should be excluded from wrapper code, False otherwise.
        """
        return self.enum_info.excluded
