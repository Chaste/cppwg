"""Free function information structure."""

from typing import Any, Dict, Optional

from cppwg.input.cpp_type_info import CppTypeInfo


class CppFreeFunctionInfo(CppTypeInfo):
    """An information structure for individual free functions to be wrapped."""

    def __init__(
        self, name: str, free_function_config: Optional[Dict[str, Any]] = None
    ):

        super(CppFreeFunctionInfo, self).__init__(name, free_function_config)

    @property
    def parent(self) -> "ModuleInfo":  # noqa: F821
        """Returns the parent module info object."""
        return self.module_info
