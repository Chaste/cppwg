"""Method information structure."""

from typing import Optional

from cppwg.input.cpp_type_info import CppTypeInfo


class CppMethodInfo(CppTypeInfo):
    """
    An information structure for individual methods to be wrapped.

    Attributes
    ----------
    class_info : CppClassInfo
        The class info parent object associated with this method
    """

    def __init__(self, name: str, _):

        super(CppMethodInfo, self).__init__(name)

        self.class_info: Optional["CppClassInfo"] = None  # noqa: F821

    @property
    def parent(self) -> "CppClassInfo":  # noqa: F821
        """Returns the parent class info object."""
        return self.class_info
