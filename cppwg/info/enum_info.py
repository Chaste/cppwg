"""Enum information structure."""

import logging
from typing import TYPE_CHECKING, Any

from cppwg.info.cpp_entity_info import CppEntityInfo

if TYPE_CHECKING:
    from pygccxml.declarations.namespace import namespace_t


class CppEnumInfo(CppEntityInfo):
    """An information structure for individual enums to be wrapped."""

    def __init__(self, name: str, enum_config: dict[str, Any] | None = None):
        super().__init__(name, enum_config)

    def update_from_ns(self, source_ns: "namespace_t") -> None:
        """
        Update with information from the source namespace.

        Adds the enum declaration.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        enum_decls = source_ns.enumerations(self.name, allow_empty=True)

        if not enum_decls:
            # The enum's header was not parsed. For explicitly listed enums, the
            # header is only included when source_file_path is set in the config.
            logger = logging.getLogger()
            logger.error(
                f"Could not find enum {self.name}. Set source_file_path "
                "in the config so that its header is included."
            )
            raise RuntimeError(f"Could not find enum: {self.name}")

        self.decls = [enum_decls[0]]
