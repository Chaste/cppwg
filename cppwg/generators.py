import os
import re
import fnmatch
import logging
import subprocess

from pathlib import Path
from typing import Optional

from pygccxml import __version__ as pygccxml_version
from pygccxml.declarations.namespace import namespace_t

from cppwg.input.class_info import CppClassInfo
from cppwg.input.free_function_info import CppFreeFunctionInfo
from cppwg.input.info_helper import CppInfoHelper
from cppwg.input.package_info import PackageInfo

from cppwg.parsers.package_info import PackageInfoParser
from cppwg.parsers.source_parser import CppSourceParser

from cppwg.writers.header_collection_writer import CppHeaderCollectionWriter
from cppwg.writers.module_writer import CppModuleWrapperWriter

from cppwg.templates import pybind11_default as wrapper_templates

from cppwg.utils.constants import CPPWG_EXT, CPPWG_HEADER_COLLECTION_FILENAME


class CppWrapperGenerator:
    """
    Main class for generating C++ wrappers

    Attributes
    ----------
    source_root : str
        The root directory of the C++ source code
    source_includes : list[str]
        The list of source include paths
    wrapper_root : str
        The output directory for the wrapper code
    castxml_binary : str
        The path to the CastXML binary
    castxml_cflags : str
        Optional cflags to be passed to CastXML e.g. "-std=c++17"
    package_info_file : str
        The path to the package info yaml config file; defaults to "package_info.yaml"
    source_hpp_files : list[str]
        The list of C++ source header files
    source_ns : namespace_t
        The namespace containing C++ declarations parsed from the source tree
    package_info : PackageInfo
        A data structure containing the information parsed from package_info_file
    """

    def __init__(
        self,
        source_root: str,
        source_includes: Optional[list[str]] = None,
        wrapper_root: Optional[str] = None,
        castxml_binary: Optional[str] = "castxml",
        package_info_file: Optional[str] = None,
        castxml_cflags: Optional[str] = "-std=c++17",
    ):
        logging.basicConfig(
            format="%(levelname)s %(message)s",
            handlers=[logging.FileHandler("filename.log"), logging.StreamHandler()],
        )
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # Sanitize source_root
        self.source_root: str = os.path.abspath(source_root)
        if not os.path.isdir(self.source_root):
            logger.error(f"Could not find source root directory: {source_root}")
            raise FileNotFoundError()

        # Sanitize wrapper_root
        self.wrapper_root: str  # type hinting
        if wrapper_root:
            # Create the specified wrapper root directory if it doesn't exist
            self.wrapper_root = os.path.abspath(wrapper_root)

            if not os.path.isdir(self.wrapper_root):
                logger.info(
                    f"Could not find wrapper root directory - creating it at {self.wrapper_root}"
                )
                os.makedirs(self.wrapper_root)
        else:
            self.wrapper_root = self.source_root
            logger.info(
                "Wrapper root not specified - using source_root: {self.source_root}"
            )

        # Sanitize source_includes
        self.source_includes: list[str]  # type hinting
        if source_includes:
            self.source_includes = [
                os.path.abspath(include_path) for include_path in source_includes
            ]

            for include_path in self.source_includes:
                if not os.path.isdir(include_path):
                    logger.error(
                        f"Could not find source include directory: {include_path}"
                    )
                    raise FileNotFoundError()
        else:
            self.source_includes = [self.source_root]

        # Sanitize package_info_file
        self.package_info_file: Optional[str] = None
        if package_info_file:
            # If a package info config file is specified, check that it exists
            self.package_info_file = package_info_file
            if not os.path.isfile(package_info_file):
                logger.error(f"Could not find package info file: {package_info_file}")
                raise FileNotFoundError()
        else:
            # If no package info config file has been supplied, check the default
            default_package_info_file = os.path.abspath("./package_info.yaml")
            if os.path.isfile(default_package_info_file):
                self.package_info_file = default_package_info_file
                logger.info(
                    f"Package info file not specified - using {default_package_info_file}"
                )
            else:
                logger.warning("No package info file found - using default settings.")

        # Check castxml and pygccxml versions
        self.castxml_binary: str = castxml_binary
        castxml_version: str = (
            subprocess.check_output([self.castxml_binary, "--version"])
            .decode("ascii")
            .strip()
        )
        castxml_version = re.search(
            r"castxml version \d+\.\d+\.\d+", castxml_version
        ).group(0)
        logger.info(castxml_version)
        logger.info(f"pygccxml version {pygccxml_version}")

        self.castxml_cflags: str = castxml_cflags

        # Initialize remaining attributes
        self.source_hpp_files: list[str] = []

        self.source_ns: Optional[namespace_t] = None

        self.package_info: Optional[PackageInfo] = None

        self.header_collection_filepath: str = os.path.join(
            self.wrapper_root, CPPWG_HEADER_COLLECTION_FILENAME
        )

    def collect_source_hpp_files(self) -> None:
        """
        Walk through the source root and add any files matching the provided
        patterns e.g. "*.hpp". Skip the wrapper root and wrappers to
        avoid pollution.
        """

        for root, _, filenames in os.walk(self.source_root, followlinks=True):
            for pattern in self.package_info.source_hpp_patterns:
                for filename in fnmatch.filter(filenames, pattern):
                    filepath = os.path.abspath(os.path.join(root, filename))

                    # Skip files in wrapper root dir
                    if Path(self.wrapper_root) in Path(filepath).parents:
                        continue

                    # Skip files with the extensions like .cppwg.hpp
                    suffix = os.path.splitext(os.path.splitext(filename)[0])[1]
                    if suffix == CPPWG_EXT:
                        continue

                    self.package_info.source_hpp_files.append(filepath)

    def extract_templates_from_source(self) -> None:
        """
        Extract template arguments for each class from the associated source file
        """

        for module_info in self.package_info.module_info_collection:
            info_helper = CppInfoHelper(module_info)
            for class_info in module_info.class_info_collection:
                info_helper.extract_templates_from_source(class_info)

    def map_classes_to_hpp_files(self) -> None:
        """
        Attempt to map source file paths to each class, assuming the containing
        file name is the class name
        """
        for module_info in self.package_info.module_info_collection:
            for class_info in module_info.class_info_collection:
                for hpp_file_path in self.package_info.source_hpp_files:
                    hpp_file_name = os.path.basename(hpp_file_path)
                    if class_info.name == os.path.splitext(hpp_file_name)[0]:
                        class_info.source_file_full_path = hpp_file_path
                        if class_info.source_file is None:
                            class_info.source_file = hpp_file_name

    def parse_header_collection(self) -> None:
        """
        Parse the headers with pygccxml and CastXML to populate the source
        namespace with C++ declarations collected from the source tree
        """

        source_parser = CppSourceParser(
            self.source_root,
            self.header_collection_filepath,
            self.castxml_binary,
            self.source_includes,
            self.castxml_cflags,
        )
        self.source_ns = source_parser.parse()

    def parse_package_info(self):
        """
        Parse the package info file to create a PackageInfo object
        """

        if self.package_info_file:
            # If a package info file exists, parse it to create a PackageInfo object
            info_parser = PackageInfoParser(self.package_info_file, self.source_root)
            self.package_info = info_parser.parse()

        else:
            # If no package info file exists, create a PackageInfo object with default settings
            self.package_info = PackageInfo("cppwg_package", self.source_root)

    def update_class_info(self) -> None:
        """
        Update the class info with class declarations parsed by pygccxml from
        the C++ source code.
        """

        for module_info in self.package_info.module_info_collection:
            if module_info.use_all_classes:
                # Create class info objects for all class declarations found
                # from parsing the source code with pygccxml.
                # Note: as module_info.use_all_classes  == True, no class info
                # objects were created while parsing the package info yaml file.
                class_decls = self.source_ns.classes(allow_empty=True)
                for class_decl in class_decls:
                    if module_info.is_decl_in_source_path(class_decl):
                        class_info = CppClassInfo(class_decl.name)
                        class_info.module_info = module_info
                        class_info.decl = class_decl
                        module_info.class_info_collection.append(class_info)

            else:
                # As module_info.use_all_classes  == False, class info objects
                # have already been created while parsing the package info file.
                # We only need to add the decl from pygccxml's output.
                for class_info in module_info.class_info_collection:
                    class_decls = self.source_ns.classes(
                        class_info.name, allow_empty=True
                    )
                    if len(class_decls) == 1:
                        class_info.decl = class_decls[0]

    def update_free_function_info(self) -> None:
        """
        Update the free function info  with declarations parsed by pygccxml from
        the C++ source code.
        """

        for module_info in self.package_info.module_info_collection:
            if module_info.use_all_free_functions:
                # Create free function info objects for all free function
                # declarations found from parsing the source code with pygccxml.
                # Note: as module_info.use_all_free_functions  == True, no class info
                # objects were created while parsing the package info yaml file.
                free_functions = self.source_ns.free_functions(allow_empty=True)
                for free_function in free_functions:
                    if module_info.is_decl_in_source_path(free_function):
                        function_info = CppFreeFunctionInfo(free_function.name)
                        function_info.module_info = module_info
                        function_info.decl = free_function
                        module_info.free_function_info.append(function_info)

            else:
                # As module_info.use_all_free_functions  == False, free function
                # info objects have already been created while parsing the
                # package info file. We only need to add the decl from pygccxml's output.
                for free_function_info in module_info.free_function_info_collection:
                    free_functions = self.source_ns.free_functions(
                        free_function_info.name, allow_empty=True
                    )
                    if len(free_functions) == 1:
                        free_function_info.decl = free_functions[0]

    def write_header_collection(self) -> None:
        """
        Write the header collection to file
        """

        header_collection_writer = CppHeaderCollectionWriter(
            self.package_info,
            self.wrapper_root,
            self.header_collection_filepath,
        )
        header_collection_writer.write()

    def write_wrappers(self) -> None:
        """
        Write all the wrappers required for the package
        """
        for module_info in self.package_info.module_info_collection:
            module_writer = CppModuleWrapperWriter(
                self.source_ns,
                module_info,
                wrapper_templates.template_collection,
                self.wrapper_root,
            )
            module_writer.write()

    def generate_wrapper(self) -> None:
        """
        Main method for generating all the wrappers
        """

        # Parse the input yaml for package, module, and class information
        self.parse_package_info()

        # Search for header files in the source root
        self.collect_source_hpp_files()

        # Map each class to a header file
        self.map_classes_to_hpp_files()

        # Attempt to extract templates for each class from the source files
        self.extract_templates_from_source()

        # Write the header collection to file
        self.write_header_collection()

        # Parse the headers with pygccxml and CastXML
        self.parse_header_collection()

        # Update the Class Info from the parsed code
        self.update_class_info()

        # Update the Free Function Info from the parsed code
        self.update_free_function_info()

        # Write all the wrappers required
        self.write_wrappers()
