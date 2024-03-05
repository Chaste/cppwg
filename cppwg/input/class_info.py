from cppwg.input.cpp_type_info import CppTypeInfo


class CppClassInfo(CppTypeInfo):
    """
    Information structure common to C++ classes
    """

    def __init__(self, name, type_info_dict=None):

        super(CppClassInfo, self).__init__(name, type_info_dict)

    @property
    def parent(self):
        return self.module_info
