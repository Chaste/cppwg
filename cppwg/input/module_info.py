"""
This file contains a list of classes that are to be wrapped.

Each class includes metadata such as template arguments, excluded methods,
methods with special pointer management requirements, and any special
declaration code needed for wrapping. A minimal case is just to
specify the class name and component it will belong to.
"""


class CppModuleInfo():

    """
    A container for each class to be wrapped. Include the class name,
    """

    def __init__(self, name, source_root, source_locations=None,
                 classes=None, free_functions=None):

        self.name = name
        self.source_locations = source_locations
        self.classes = classes
        self.class_info = None
        self.source_root = source_root
        self.free_functions = free_functions
        self.free_function_info = None

    def using_all_free_functions(self):

        if isinstance(self.free_functions, basestring):
            cleaned = self.free_functions.strip().upper()
            if cleaned == 'CPPWG_ALL':
                return True

        return False

    def using_all_classes(self):

        if isinstance(self.classes, basestring):
            cleaned = self.classes.strip().upper()
            if cleaned == 'CPPWG_ALL':
                return True

        return False

    def decl_in_source_path(self, decl):

        if self.source_locations is None:
            return True

        for eachSourceLocation in self.source_locations:
            location = self.source_root + "/" + eachSourceLocation + "/"
            if location in decl.location.file_name:
                return True
        return False
