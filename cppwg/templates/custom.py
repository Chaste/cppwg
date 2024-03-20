class Custom:
    """
    This class returns custom code snippets for use during the wrapper
    generation processes. It can be used as a base classs for
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

    def get_module_code(self) -> str:
        """
        Return a string of C++ code to be inserted in the module
        definition.
        """

        return ""
