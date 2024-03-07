from typing import Optional

from cppwg.input.cpp_type_info import CppTypeInfo


class CppMethodInfo(CppTypeInfo):
    """
    This class holds information for individual methods to be wrapped

    Attributes
    ----------
    class_info : CppClassInfo
        The class info parent object associated with this method
    """

    def __init__(self, name: str, _):

        super(CppMethodInfo, self).__init__(name)

        self.class_info: Optional["CppClassInfo"] = None

    @property
    def parent(self) -> "CppClassInfo":
        """
        Returns the parent class info object
        """
        return self.class_info
