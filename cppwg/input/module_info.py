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

    def __init__(self, name, source_locations=None,
                 classes=None, free_functions=None):

        self.name = name
        self.source_locations = source_locations
        self.classes = classes
        self.free_functions = free_functions
