"""
Information for methods
"""

from cppwg.input import cpp_type_info


class CppMethodInfo(cpp_type_info.CppTypeInfo):

    """
    A container for method types to be wrapped
    """

    def __init__(self, name, _):
        
        super(CppMethodInfo, self).__init__(name)
        
        self.class_info = None
        
    @property
    def parent(self):
        return self.class_info
        
    

