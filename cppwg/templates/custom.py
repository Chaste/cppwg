class Custom:
    """
    This class returns custom code snippets for use during the wrapper
    generation processes. It can be used as a base class for
    custom code generators.
    """

    def __init__(self):

        pass

    def get_class_cpp_pre_code(self, *args, **kwargs) -> str:
        """
        Return a string of C++ code to be inserted before the class
        definition.
        """

        return ""

    def get_class_cpp_def_code(self, *args, **kwargs) -> str:
        """
        Return a string of C++ code to be inserted in the class
        definition.
        """

        return ""

    def get_source_includes(self, *args, **kwargs) -> list:
        """
        Return headers to add to the #include block of the class wrapper.

        Use this for headers the generated code needs but that cppwg cannot
        infer from the parsed C++ signatures - e.g. types named only inside the
        get_class_cpp_def_code() output, which auto-include detection never sees.
        Each entry is spelled as under source_includes: a bare name (Foo.hpp)
        becomes a quoted include (#include "Foo.hpp") and an angle-bracket form
        (<foo>) becomes a system include (#include <foo>). cppwg adds the quotes,
        so do not wrap the name in quotes yourself. Returns an empty list by
        default.
        """

        return []

    def get_module_pre_code(self) -> str:
        """
        Return a string of C++ code to be inserted before the module
        definition.
        """

        return ""

    def get_module_code(self) -> str:
        """
        Return a string of C++ code to be inserted in the module
        definition.
        """

        return ""
