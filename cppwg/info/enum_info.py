"""Enum information structure."""

import logging
from typing import TYPE_CHECKING, Any

from cppwg.info.cpp_entity_info import CppEntityInfo
from cppwg.utils import utils

if TYPE_CHECKING:
    from pygccxml.declarations.namespace import namespace_t


class CppEnumInfo(CppEntityInfo):
    """
    An information structure for individual enums to be wrapped.

    Attributes
    ----------
    scoped : bool
        Whether the enum is a scoped enum (`enum class`/`enum struct`). Scoped
        enums do not export their enumerators into the enclosing scope, so
        pybind11's `.export_values()` is omitted for them by default.
    Note
    ----
    The inheritable `export_values` config option (defined on BaseInfo) overrides
    whether `.export_values()` is emitted; see should_export_values.
    """

    def __init__(self, name: str, enum_config: dict[str, Any] | None = None):
        super().__init__(name, enum_config)

        self.scoped: bool = False

    def should_export_values(self) -> bool:
        """
        Return whether to emit pybind11's `.export_values()` for this enum.

        The `export_values` config option wins if set at this enum or anywhere up
        the info tree (package/module); otherwise mirror the C++ enum kind -
        export for an unscoped enum, not for a scoped one.
        """
        return utils.should_export_enum_values(
            self.hierarchy_attribute("export_values"), self.scoped
        )

    def update_from_ns(self, source_ns: "namespace_t") -> None:
        """
        Update with information from the source namespace.

        Adds the enum declaration and records whether the enum is scoped.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        enum_decls = source_ns.enumerations(self.name, allow_empty=True)

        if not enum_decls:
            # The enum's header was not parsed. For an explicitly listed enum,
            # set source_file or source_file_path so its header is included -
            # unless it is already pulled in by another wrapped entity declared
            # in the same header.
            logger = logging.getLogger()
            logger.error(
                f"Could not find enum {self.name}. Set source_file or "
                "source_file_path in the config so that its header is included."
            )
            raise RuntimeError(f"Could not find enum: {self.name}")

        self.decls = [enum_decls[0]]

        # pygccxml does not expose enum scopedness, so read it from the source
        # file the enum was declared in (via the resolved decl's location).
        self.scoped = utils.is_scoped_enum_in_source_file(
            self.decls[0].location.file_name, self.decls[0].name
        )
