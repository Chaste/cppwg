from typing import Any, Dict, Optional

from cppwg.input.cpp_type_info import CppTypeInfo


class CppVariableInfo(CppTypeInfo):
    """
    This class holds information for individual variables to be wrapped
    """

    def __init__(self, name: str, variable_config: Optional[Dict[str, Any]] = None):

        super(CppVariableInfo, self).__init__(name, variable_config)
