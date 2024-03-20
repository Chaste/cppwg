"""
cppwg: an automatic Python wrapper generator for C++ code.

Available subpackages
---------------------
generators
    Contains the main interface for generating Python wrappers.
input
    Contains information structures for C++ code to be wrapped.
parsers
    Contains parsers for C++ code and input yaml.
templates
    Contains string templates for Python wrappers.
utils
    Contains utility functions and constants.
writers
    Contains writers for creating Python wrappers and writing to file.

Utilities
---------
__version__
    cppwg version string
"""

from importlib import metadata

from cppwg.generators import CppWrapperGenerator

__all__ = [
    "CppWrapperGenerator",
]

__version__ = metadata.version("cppwg")
