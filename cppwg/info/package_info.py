"""Package information structure."""

import fnmatch
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pygccxml import declarations

from cppwg.info.base_info import BaseInfo
from cppwg.utils import utils
from cppwg.utils.constants import CPPWG_EXT


class PackageInfo(BaseInfo):
    """
    A structure to hold information about the package.

    Attributes
    ----------
    common_include_file : bool
        Use a common include file for all source files
    exceptions : List[Union[str, Dict[str, str]]]
        C++ exception classes to translate into Python exceptions. Each entry is
        a class name, or a dict with a `name` and an optional `message_method`
        (the accessor for the message, defaulting to "what"). A pybind11
        exception translator is generated automatically for each.
    exclude_default_args : bool
        Exclude default arguments from method wrappers.
    name : str
        The name of the package
    source_hpp_patterns : List[str]
        A list of source file patterns to include

    exception_info : List[Dict[str, str]]
        Resolved exception translation data (cpp_type, message_expr,
        source_file), populated from `exceptions` after parsing the source.
    module_collection : List[ModuleInfo]
        A list of module info objects associated with this package
    source_hpp_files : List[str]
        A list of source file names to include
    """

    def __init__(
        self, name: str, package_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Create a package info object from a package_config dict.

        Parameters
        ----------
        name : str
            The name of the package
        package_config : Dict[str, Any]
            A dictionary of package configuration settings
        """
        super().__init__(name, package_config)

        self.common_include_file: bool = False
        self.exceptions: List[Union[str, Dict[str, str]]] = []
        self.exclude_default_args: bool = False
        self.source_hpp_patterns: List[str] = ["*.hpp"]

        self.exception_info: List[Dict[str, str]] = []
        self.module_collection: List["ModuleInfo"] = []  # noqa: F821
        self.source_hpp_files: List[str] = []

        if package_config:
            self.common_include_file = package_config.get(
                "common_include_file", self.common_include_file
            )
            self.exceptions = package_config.get("exceptions", self.exceptions)
            self.exclude_default_args = package_config.get(
                "exclude_default_args", self.exclude_default_args
            )
            self.source_hpp_patterns = package_config.get(
                "source_hpp_patterns", self.source_hpp_patterns
            )

    @property
    def parent(self) -> None:
        """
        Returns None, as this is the top level of the info tree hierarchy.
        """
        return None

    def add_module(self, module_info: "ModuleInfo") -> None:  # noqa: F821
        """
        Add a module info object to the package.

        Parameters
        ----------
        module_info : ModuleInfo
            The module info object to add
        """
        self.module_collection.append(module_info)
        module_info.parent = self

    def init(self, restricted_paths: List[str]) -> None:
        """
        Initialise - collect header files and update info.

        Parameters
        ----------
        restricted_paths : List[str]
            A list of restricted paths to skip when collecting header files.
        """
        self.collect_source_headers(restricted_paths)
        self.update_from_source()

    def collect_source_headers(self, restricted_paths: List[str]) -> None:
        """
        Collect header files from the source root.

        Walk through the source root and add any files matching the provided
        source file patterns e.g. "*.hpp".

        Parameters
        ----------
        restricted_paths : List[str]
            A list of restricted paths to skip when collecting header files.
        """
        logger = logging.getLogger()

        for root, _, filenames in os.walk(self.source_root, followlinks=True):
            for pattern in self.source_hpp_patterns:
                for filename in fnmatch.filter(filenames, pattern):
                    filepath = os.path.abspath(os.path.join(root, filename))

                    # Skip files in restricted paths
                    for restricted_path in restricted_paths:
                        if Path(restricted_path) in Path(filepath).parents:
                            continue

                    # Skip files with the extensions like .cppwg.hpp
                    suffix = os.path.splitext(os.path.splitext(filename)[0])[1]
                    if suffix == CPPWG_EXT:
                        continue

                    self.source_hpp_files.append(filepath)

        # Check if any source files were found
        if not self.source_hpp_files:
            logger.error(f"No header files found in source root: {self.source_root}")
            raise FileNotFoundError()

        # Sort by filename
        self.source_hpp_files.sort(key=lambda x: os.path.basename(x))

    def update_from_source(self) -> None:
        """
        Update with data from the source headers.
        """
        for module_info in self.module_collection:
            module_info.update_from_source(self.source_hpp_files)

    def update_from_ns(self, source_ns: "namespace_t") -> None:  # noqa: F821
        """
        Update modules with information from the parsed source namespace.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        for module_info in self.module_collection:
            module_info.update_from_ns(source_ns)

        self.resolve_exceptions(source_ns)

    @staticmethod
    def parse_exception_entry(entry: Any) -> Tuple[str, str]:
        """
        Return the (class name, message method) for an exceptions config entry.

        An entry may be a bare class name string, or a dict with a `name` and an
        optional `message_method` (defaulting to "what").

        Parameters
        ----------
        entry : Any
            A single entry from the `exceptions` config list.

        Returns
        -------
        Tuple[str, str]
            The exception class name and the message accessor method name.
        """
        if isinstance(entry, dict):
            return entry["name"], entry.get("message_method", "what")
        return entry, "what"

    @property
    def exception_names(self) -> List[str]:
        """Return the names of the configured exception classes."""
        return [self.parse_exception_entry(entry)[0] for entry in self.exceptions]

    def resolve_exceptions(self, source_ns: "namespace_t") -> None:  # noqa: F821
        """
        Resolve exception config entries into translation data.

        For each entry in `exceptions`, look up the class in the source
        namespace, work out how to extract its message (calling the configured
        message_method, defaulting to what(), and adding .c_str() unless it
        already returns a pointer), and find which header declares it. The
        result is used to generate a pybind11 exception translator per module.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        logger = logging.getLogger()

        self.exception_info = []
        for entry in self.exceptions:
            name, message_method = self.parse_exception_entry(entry)

            class_decls = source_ns.classes(
                lambda decl: decl.name == name, allow_empty=True  # noqa: B023
            )

            if not class_decls:
                logger.error(f"Could not find exception class {name}.")
                raise RuntimeError(f"Could not find exception class: {name}")

            class_decl = class_decls[0]

            # Check the class (and its base classes, e.g. for an inherited
            # what()) actually declares the configured message method.
            method_decl = utils.find_member_function(class_decl, message_method)
            if method_decl is None:
                logger.error(f"Exception class {name} has no method {message_method}.")
                raise RuntimeError(
                    f"Exception class {name} has no method: {message_method}"
                )

            # PyErr_SetString needs a const char*. Add .c_str() unless the
            # message method already returns a pointer (e.g. what()).
            message_expr = f"e.{message_method}()"
            if not declarations.is_pointer(method_decl.return_type):
                message_expr += ".c_str()"

            self.exception_info.append(
                {
                    "cpp_type": name,
                    "message_expr": message_expr,
                    "source_file": os.path.basename(class_decl.location.file_name),
                }
            )
