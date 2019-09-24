"""
Information for variables
"""

from cppwg.input import cpp_type_info


class CppVariableInfo(cpp_type_info.CppTypeInfo):

    """
    A container for variable types to be wrapped
    """

    def __init__(self, name, type_info_dict = None):
        
        super(CppVariableInfo, self).__init__(name, type_info_dict)

