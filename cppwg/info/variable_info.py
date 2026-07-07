"""Variable information structure."""

from typing import Any

from cppwg.info.cpp_entity_info import CppEntityInfo


class CppVariableInfo(CppEntityInfo):
    """An information structure for individual variables to be wrapped."""

    def __init__(self, name: str, variable_config: dict[str, Any] | None = None):
        super().__init__(name, variable_config)
