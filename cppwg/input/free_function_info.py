"""
This file contains a list of classes that are to be wrapped.

Each class includes metadata such as template arguments, excluded methods,
methods with special pointer management requirements, and any special
declaration code needed for wrapping. A minimal case is just to
specify the class name and component it will belong to.
"""


class CppFreeFunctionInfo():

    """
    A container for free function types to be wrapped
    """

    def __init__(self, name, module):
        self.name = name
        self.module = module
        self.decl = None

