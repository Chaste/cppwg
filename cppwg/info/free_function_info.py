"""Free function information structure."""

import logging
from typing import Any, Dict, Optional

from cppwg.info.cpp_entity_info import CppEntityInfo


class CppFreeFunctionInfo(CppEntityInfo):
    """An information structure for individual free functions to be wrapped."""

    def __init__(
        self, name: str, free_function_config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(name, free_function_config)

    def update_from_ns(self, source_ns: "namespace_t") -> None:  # noqa: F821
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
            # The function's header was not parsed. For explicitly listed free
            # functions, the header is only included when source_file or
            # source_file_path is set in the config.
            logger = logging.getLogger()
            logger.error(
                f"Could not find free function {self.name}. Set source_file or "
                "source_file_path in the config so that its header is included."
            )
            raise RuntimeError(f"Could not find free function: {self.name}")

        self.decls = [ff_decls[0]]
