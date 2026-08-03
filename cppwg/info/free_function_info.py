"""Free function information structure."""

import logging
from typing import TYPE_CHECKING, Any

from cppwg.info.cpp_entity_info import CppEntityInfo

if TYPE_CHECKING:
    from pygccxml.declarations.namespace import namespace_t


class CppFreeFunctionInfo(CppEntityInfo):
    """An information structure for individual free functions to be wrapped."""

    def __init__(self, name: str, free_function_config: dict[str, Any] | None = None):
        super().__init__(name, free_function_config)

    def update_from_ns(self, source_ns: "namespace_t") -> None:
        """
        Update with information from the source namespace.

        Adds the free function declaration.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        ff_decls = source_ns.free_functions(self.name, allow_empty=True)

        if not ff_decls:
            # The function's header was not parsed. For an explicitly listed free
            # function, set source_file or source_file_path so its header is
            # included - unless it is already pulled in by another wrapped entity
            # declared in the same header.
            logger = logging.getLogger()
            logger.error(
                f"Could not find free function {self.name}. Set source_file or "
                "source_file_path in the config so that its header is included."
            )
            raise RuntimeError(f"Could not find free function: {self.name}")

        self.decls = [ff_decls[0]]
