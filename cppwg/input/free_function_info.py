"""
Information for free functions
"""

from cppwg.input import cpp_type_info


class CppFreeFunctionInfo(cpp_type_info.CppTypeInfo):

    """
    A container for free function types to be wrapped
    """

    def __init__(self, name, type_info_dict = None):
        
        super(CppFreeFunctionInfo, self).__init__(name, type_info_dict)

    @property
    def parent(self):
        return self.module_info