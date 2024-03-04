import os
import re
import fnmatch
import logging
import subprocess

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

import cppwg.templates.pybind11_default as wrapper_templates


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
    ):
        logging.basicConfig(
            format="%(levelname)s %(message)s",
            handlers=[logging.FileHandler("filename.log"), logging.StreamHandler()],
        )
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # Sanitize source_root
        self.source_root: str = os.path.realpath(source_root)
        if not os.path.exists(self.source_root):
            message = f"Could not find source root directory: {source_root}"
            logger.error(message)
            raise FileNotFoundError()

        # Sanitize wrapper_root
        self.wrapper_root: str  # type hinting
        if wrapper_root:
            self.wrapper_root = os.path.realpath(wrapper_root)

            if not os.path.exists(self.wrapper_root):
                message = f"Could not find wrapper root directory: {wrapper_root}"
                logger.error(message)
                raise FileNotFoundError()
        else:
            self.wrapper_root = self.source_root
            logger.info(
                "Wrapper root not specified - using source_root: {self.source_root}"
            )

        # Sanitize source_includes
        self.source_includes: list[str]  # type hinting
        if source_includes:
            self.source_includes = [
                os.path.realpath(include_path) for include_path in source_includes
            ]

            for include_path in self.source_includes:
                if not os.path.exists(include_path):
                    message = f"Could not find source include directory: {include_path}"
                    logger.error(message)
                    raise FileNotFoundError()
        else:
            self.source_includes = [self.source_root]

        # Sanitize package_info_file
        self.package_info_file: Optional[str] = None
        if package_info_file:
            # If a package info config file is specified, check that it exists
            self.package_info_file = package_info_file
            if not os.path.exists(package_info_file):
                message = f"Could not find package info file: {package_info_file}"
                logger.error(message)
                raise FileNotFoundError()
        else:
            # If no package info config file has been supplied, check the default
            default_package_info_file = os.path.realpath("./package_info.yaml")
            if os.path.exists(default_package_info_file):
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

        # Initialize remaining attributes
        self.source_hpp_files: list[str] = []

        self.source_ns: Optional[namespace_t] = None

        self.package_info: Optional[PackageInfo] = None

    def collect_source_hpp_files(self):
        """
        Walk through the source root and add any files matching the provided patterns.
        Keep the wrapper root out of the search path to avoid pollution.
        """
        for root, _, filenames in os.walk(self.source_root, followlinks=True):
            for pattern in self.package_info.source_hpp_patterns:
                for filename in fnmatch.filter(filenames, pattern):
                    if "cppwg" not in filename:
                        self.package_info.source_hpp_files.append(
                            os.path.join(root, filename)
                        )
        self.package_info.source_hpp_files = [
            path
            for path in self.package_info.source_hpp_files
            if self.wrapper_root not in path
        ]

    def generate_header_collection(self):
        """
        Write the header collection to file
        """

        header_collection_writer = CppHeaderCollectionWriter(
            self.package_info, self.wrapper_root
        )
        header_collection_writer.write()
        header_collection_path = self.wrapper_root + "/"
        header_collection_path += header_collection_writer.header_file_name

        return header_collection_path

    def parse_header_collection(self, header_collection_path: str):
        """
        Parse the headers with pygccxml and CastXML to populate the source
        namespace with C++ declarations collected from the source tree

        Parameters
        ----------
            header_collection_path : str
                The path to the header collection file
        """

        source_parser = CppSourceParser(
            self.source_root,
            header_collection_path,
            self.castxml_binary,
            self.source_includes,
        )
        self.source_ns = source_parser.parse()

    def parse_package_info(self):
        """
        Parse the package info file to create a PackageInfo object
        """

        if self.package_info_file:
            # If a package info file exists, parse it to create a PackageInfo object
            info_parser = PackageInfoParser(self.package_info_file, self.source_root)
            info_parser.parse()
            self.package_info = info_parser.package_info

        else:
            # If no package info file exists, create a PackageInfo object with default settings
            self.package_info = PackageInfo("cppwg_package", self.source_root)

    def update_free_function_info(self):
        """
        Update the free function info pased on pygccxml output
        """

        for eachModule in self.package_info.module_info:
            if eachModule.use_all_free_functions:
                free_functions = self.source_ns.free_functions(allow_empty=True)
                for eachFunction in free_functions:
                    if eachModule.is_decl_in_source_path(eachFunction):
                        function_info = CppFreeFunctionInfo(eachFunction.name)
                        function_info.module_info = eachModule
                        function_info.decl = eachFunction
                        eachModule.free_function_info.append(function_info)

            else:
                for eachFunction in eachModule.free_function_info:
                    functions = self.source_ns.free_functions(
                        eachFunction.name, allow_empty=True
                    )
                    if len(functions) == 1:
                        eachFunction.decl = functions[0]

    def update_class_info(self):
        """
        Update the class info pased on pygccxml output
        """

        for eachModule in self.package_info.module_info:
            if eachModule.use_all_classes:
                classes = self.source_ns.classes(allow_empty=True)
                for eachClass in classes:
                    if eachModule.is_decl_in_source_path(eachClass):
                        class_info = CppClassInfo(eachClass.name)
                        class_info.module_info = eachModule
                        class_info.decl = eachClass
                        eachModule.class_info.append(class_info)
            else:
                for eachClass in eachModule.class_info:
                    classes = self.source_ns.classes(eachClass.name, allow_empty=True)
                    if len(classes) == 1:
                        eachClass.decl = classes[0]

    def generate_wrapper(self):
        """
        Main method for generating all the wrappers
        """

        # Parse the package info file
        self.parse_package_info()

        # Generate a header collection
        self.collect_source_hpp_files()

        # Attempt to assign source paths to each class, assuming the containing
        # file name is the class name
        for eachModule in self.package_info.module_info:
            for eachClass in eachModule.class_info:
                for eachPath in self.package_info.source_hpp_files:
                    base = os.path.basename(eachPath)
                    if eachClass.name == base.split(".")[0]:
                        eachClass.source_file_full_path = eachPath
                        if eachClass.source_file is None:
                            eachClass.source_file = base

        # Attempt to automatically generate template args for each class
        for eachModule in self.package_info.module_info:
            info_genenerator = CppInfoHelper(eachModule)
            for eachClass in eachModule.class_info:
                info_genenerator.expand_templates(eachClass, "class")

        # Generate the header collection
        header_collection_path = self.generate_header_collection()

        # Parse the header collection
        self.parse_header_collection(header_collection_path)

        # Update the Class and Free Function Info from the parsed code
        self.update_class_info()
        self.update_free_function_info()

        # Write all the wrappers required for each module
        for module_info in self.package_info.module_info:
            module_writer = CppModuleWrapperWriter(
                self.source_ns,
                module_info,
                wrapper_templates.template_collection,
                self.wrapper_root,
            )
            module_writer.write()
