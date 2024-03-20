"""Class information structure."""

from typing import Any, Dict, Optional

from cppwg.input.cpp_type_info import CppTypeInfo


class CppClassInfo(CppTypeInfo):
    """An information structure for individual C++ classes to be wrapped."""

    def __init__(self, name: str, class_config: Optional[Dict[str, Any]] = None):

        super(CppClassInfo, self).__init__(name, class_config)

    @property
    def parent(self) -> "ModuleInfo":  # noqa: F821
        """Returns the parent module info object."""
        return self.module_info
