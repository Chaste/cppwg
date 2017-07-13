"""
Information structure common to C++ classes
"""

import cpp_type_info


class CppClassInfo(cpp_type_info.CppTypeInfo):


    def __init__(self, name, type_info_dict = None):
        
        super(CppClassInfo, self).__init__(name, type_info_dict)
        
    @property
    def parent(self):
        return self.module_info
