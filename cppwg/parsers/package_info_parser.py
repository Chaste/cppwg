"""Parser for input yaml."""

import logging
import os
from typing import Any

import yaml

from cppwg.info.class_info import CppClassInfo
from cppwg.info.free_function_info import CppFreeFunctionInfo
from cppwg.info.module_info import ModuleInfo
from cppwg.info.package_info import PackageInfo
from cppwg.info.variable_info import CppVariableInfo
from cppwg.utils import utils
from cppwg.utils.constants import CPPWG_SOURCEROOT_STRING


class PackageInfoParser:
    """
    Parser for the package info yaml file.

    Attributes
    ----------
        config_file : str
            The path to the package info yaml config file
        source_root : str
            The root directory of the C++ source code
    """

    def __init__(self, config_file: str, source_root: str):
        self.config_file = config_file
        self.source_root = source_root

    def parse(self) -> PackageInfo:
        """
        Parse the yaml file.

        Parse the package info yaml file to extract information about the
        package, modules, classes, and free functions.

        Returns
        -------
        PackageInfo
            The object holding data from the parsed package info yaml file.
        """
        logger = logging.getLogger()
        logger.info("Parsing package info file.")

        # Load raw info from the yaml file
        raw_package_info: dict[str, Any] = {}

        with open(self.config_file) as config_file:
            raw_package_info = yaml.safe_load(config_file)

        # Base config options that apply to package, modules, classes, etc.
        base_config: dict[str, Any] = {
            "calldef_excludes": "",
            "constructor_arg_type_excludes": "",
            "constructor_signature_excludes": "",
            "custom_generator": "",
            "excluded": False,
            "excluded_methods": [],
            "excluded_variables": [],
            "extra_code": [],
            "pointer_call_policy": "",
            "prefix_code": [],
            "prefix_text": "",
            "reference_call_policy": "",
            "return_type_excludes": "",
            "smart_ptr_type": "",
            "source_includes": [],
            "source_root": self.source_root,
            "suffix_code": [],
            "template_substitutions": [],
        }

        # Get package config from the raw package info
        package_config: dict[str, Any] = {
            "name": "cppwg_package",
            "common_include_file": True,
            "exceptions": [],
            "exclude_default_args": False,
            "source_hpp_patterns": ["*.hpp"],
        }
        package_config.update(base_config)

        for key in package_config.keys():
            if key in raw_package_info:
                package_config[key] = raw_package_info[key]

        # Replace boolean strings with booleans
        package_config["common_include_file"] = utils.convert_to_bool(
            package_config["common_include_file"]
        )
        package_config["exclude_default_args"] = utils.convert_to_bool(
            package_config["exclude_default_args"]
        )

        # Convert custom generator path to a full path
        self.convert_custom_generator(package_config)

        # Create the PackageInfo object from the package config dict
        package_info = PackageInfo(package_config["name"], package_config)

        # Parse the module data
        for raw_module_info in raw_package_info["modules"]:
            # Get module config from the raw module info
            module_config = {
                "name": "cppwg_module",
                "external_bases": [],
                "imports": [],
                "source_locations": [],
                "use_all_classes": False,
                "use_all_free_functions": False,
                "use_all_variables": False,
                "classes": [],
                "free_functions": [],
                "variables": [],
            }
            module_config.update(base_config)

            for key in module_config.keys():
                if key in raw_module_info:
                    module_config[key] = raw_module_info[key]

            # Convert source locations to full paths
            if module_config["source_locations"]:
                locations = []
                for location in module_config["source_locations"]:
                    locations.append(self.full_path(location))
                    self.verify_path(locations[-1])
                module_config["source_locations"] = locations

            # Convert custom generator path to a full path
            self.convert_custom_generator(module_config)

            # Convert boolean options
            module_config["use_all_classes"] = utils.is_option_ALL(
                module_config["classes"]
            )

            module_config["use_all_free_functions"] = utils.is_option_ALL(
                module_config["free_functions"]
            )

            module_config["use_all_variables"] = utils.is_option_ALL(
                module_config["variables"]
            )

            # Create the ModuleInfo object from the module config dict
            module_info = ModuleInfo(module_config["name"], module_config)

            # Add the module to the package
            package_info.add_module(module_info)

            # Parse the class data and create class info objects.
            # Note: if module_config["use_all_classes"] == True, class info
            # objects will be added later after parsing the C++ source code.
            if not module_config["use_all_classes"]:
                if module_config["classes"]:
                    for raw_class_info in module_config["classes"]:
                        # Get class config from the raw class info
                        class_config = {
                            "name_override": "",
                            "source_file": "",
                            "source_file_path": "",
                        }
                        class_config.update(base_config)

                        for key in class_config.keys():
                            if key in raw_class_info:
                                class_config[key] = raw_class_info[key]

                        # Convert source file path to a full path
                        class_config["source_file_path"] = self.full_path(
                            class_config["source_file_path"]
                        )
                        self.verify_path(class_config["source_file_path"])

                        # Convert custom generator path to a full path
                        self.convert_custom_generator(class_config)

                        # Create the CppClassInfo object from the class config dict
                        class_info = CppClassInfo(raw_class_info["name"], class_config)

                        # Add the class to the module
                        module_info.add_class(class_info)

            # Parse the free function data and create free function info objects.
            # Note: if module_config["use_all_free_functions"] == True, free function
            # info objects will be added later after parsing the C++ source code.
            if not module_config["use_all_free_functions"]:
                if module_config["free_functions"]:
                    for raw_free_function_info in module_config["free_functions"]:
                        # Get free function config from the raw free function info
                        free_function_config = {
                            "name_override": "",
                            "source_file": "",
                            "source_file_path": "",
                        }
                        free_function_config.update(base_config)

                        for key in free_function_config.keys():
                            if key in raw_free_function_info:
                                free_function_config[key] = raw_free_function_info[key]

                        # Convert source file path to a full path
                        free_function_config["source_file_path"] = self.full_path(
                            free_function_config["source_file_path"]
                        )
                        self.verify_path(free_function_config["source_file_path"])

                        # Convert custom generator path to a full path
                        self.convert_custom_generator(free_function_config)

                        # Create the CppFreeFunctionInfo object from the free function config dict
                        free_function_info = CppFreeFunctionInfo(
                            raw_free_function_info["name"], free_function_config
                        )

                        # Add the free function to the module
                        module_info.add_free_function(free_function_info)

            # Parse the variable data
            if not module_config["use_all_variables"]:
                if module_config["variables"]:
                    for raw_variable_info in module_config["variables"]:
                        # Get variable config from the raw variable info
                        variable_config = {
                            "name_override": "",
                            "source_file": "",
                            "source_file_path": "",
                        }
                        variable_config.update(base_config)

                        for key in variable_config.keys():
                            if key in raw_variable_info:
                                variable_config[key] = raw_variable_info[key]

                        # Convert source file path to a full path
                        variable_config["source_file_path"] = self.full_path(
                            variable_config["source_file_path"]
                        )
                        self.verify_path(variable_config["source_file_path"])

                        # Convert custom generator path to a full path
                        self.convert_custom_generator(variable_config)

                        # Create the CppVariableInfo object from the variable config dict
                        variable_info = CppVariableInfo(
                            variable_config["name"], variable_config
                        )

                        # Add the variable to the module
                        module_info.add_variable(variable_info)

        return package_info

    def convert_custom_generator(self, config: dict[str, Any]) -> None:
        """
        Convert the custom generator path to a full path if set in the config.

        Parameters
        ----------
        config: dict[str, Any]
            The config dictionary.
        """
        if not config["custom_generator"]:
            return

        config["custom_generator"] = self.convert_path(config["custom_generator"])
        self.verify_path(config["custom_generator"])

    def convert_path(self, raw_path: str) -> str:
        """
        Convert a path which has a CPPWG_SOURCEROOT_STRING placeholder.

        Parameters
        ----------
        raw_path: str
            The path to convert.
        """
        if not raw_path:
            return ""
        path = raw_path.replace(CPPWG_SOURCEROOT_STRING, self.source_root)
        return os.path.abspath(path)

    def full_path(self, relative_path: str) -> str:
        """
        Get the full path for a path specified relative to the source root.

        Parameters
        ----------
        relative_path: str
            The path relative to the source root.
        """
        if not relative_path:
            return ""
        path = os.path.join(self.source_root, relative_path)
        return os.path.abspath(path)

    def verify_path(self, path: str) -> None:
        """
        Verify that the path exists if set.

        Parameters
        ----------
        path: str
            The path.
        """
        if not path:
            return

        logger = logging.getLogger()
        if not os.path.exists(path):
            logger.error(f"Could not find {path}")
            raise FileNotFoundError()
