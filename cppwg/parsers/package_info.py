import os
import importlib.util
import logging
import sys
import yaml

from typing import Any, Optional

import cppwg.templates.custom

from cppwg.input.base_info import BaseInfo
from cppwg.input.class_info import CppClassInfo
from cppwg.input.free_function_info import CppFreeFunctionInfo
from cppwg.input.module_info import ModuleInfo
from cppwg.input.package_info import PackageInfo

from cppwg.utils import utils
from cppwg.utils.constants import CPPWG_SOURCEROOT_STRING


class PackageInfoParser:
    """
    Parse for the package info yaml file

    Attributes
    ----------
        input_filepath : str
            The path to the package info yaml file
        source_root : str
            The root directory of the C++ source code
        raw_package_info : dict[str, Any]
            Raw info from the yaml file
        package_info : Optional[PackageInfo]
            The parsed package info
    """

    def __init__(self, input_filepath: str, source_root: str):
        """
        Parameters
        ----------
            input_filepath : str
                The path to the package info yaml file.
            source_root : str
                The root directory of the C++ source code.
        """

        self.input_filepath: str = input_filepath
        self.source_root: str = source_root

        # For holding raw info from the yaml file
        self.raw_package_info: dict[str, Any] = {}

        # The parsed package info
        self.package_info: Optional[PackageInfo] = None

    def check_for_custom_generators(self, info: BaseInfo) -> None:
        """
        Check if a custom generator is specified and load it into a module.

        Parameters
        ----------
        info : BaseInfo
            The info object to check for a custom generator - might be info
            about a package, module, class, or free function.
        """
        logger = logging.getLogger()

        if not info.custom_generator:
            return

        # Replace the `CPPWG_SOURCEROOT` placeholder in the custom generator
        # string if needed. For example, a custom generator might be specified
        # as `custom_generator: CPPWG_SOURCEROOT/path/to/CustomGenerator.py`
        filepath: str = info.custom_generator.replace(
           CPPWG_SOURCEROOT_STRING, self.source_root
        )
        filepath = os.path.abspath(filepath)

        # Verify that the custom generator file exists
        if not os.path.isfile(filepath):
            logger.error(
                f"Could not find specified custom generator for {info.name}: {filepath}"
            )
            raise FileNotFoundError()

        logger.info(f"Custom generator for {info.name}: {filepath}")

        # Load the custom generator as a module
        module_name: str = os.path.splitext(filepath)[0]  # /path/to/CustomGenerator
        class_name: str = os.path.basename(module_name)  # CustomGenerator

        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Get the custom generator class from the loaded module.
        # Note: The custom generator class name must match the filename.
        CustomGeneratorClass: cppwg.templates.custom.Custom = getattr(
            module, class_name
        )

        # Replace the `info.custom_generator` string with a new object created
        # from the provided custom generator class
        info.custom_generator = CustomGeneratorClass()

    def parse(self) -> PackageInfo:
        """
        Parse the package info yaml file to extract information about the
        package, modules, classes, and free functions.

        Returns
        -------
        PackageInfo
            The object holding data from the parsed package info yaml file.
        """
        logger = logging.getLogger()
        logger.info("Parsing package info file.")

        with open(self.input_filepath, "r") as input_filepath:
            self.raw_package_info = yaml.safe_load(input_filepath)

        # Default config options that apply to the package, modules, classes, and free functions
        global_config: dict[str, Any] = {
            "source_includes": [],
            "smart_ptr_type": None,
            "calldef_excludes": None,
            "return_type_excludes": None,
            "template_substitutions": [],
            "pointer_call_policy": None,
            "reference_call_policy": None,
            "constructor_arg_type_excludes": None,
            "excluded_methods": [],
            "excluded_variables": [],
            "custom_generator": None,
            "prefix_code": [],
        }

        # Get package config from the raw package info
        package_config: dict[str, Any] = {
            "name": "cppwg_package",
            "common_include_file": True,
            "source_hpp_patterns": ["*.hpp"],
        }
        package_config.update(global_config)

        for key in package_config.keys():
            if key in self.raw_package_info:
                package_config[key] = self.raw_package_info[key]
        utils.substitute_bool_for_string(package_config, "common_include_file")

        # Create the PackageInfo object from the package config dict
        self.package_info = PackageInfo(
            package_config["name"], self.source_root, package_config
        )
        self.check_for_custom_generators(self.package_info)

        # Parse the module data
        for raw_module_info in self.raw_package_info["modules"]:
            # Get module config from the raw module info
            module_config = {
                "name": "cppwg_module",
                "source_locations": None,
                "classes": [],
                "free_functions": [],
                "variables": [],
                "use_all_classes": False,
                "use_all_free_functions": False,
            }
            module_config.update(global_config)

            for key in module_config.keys():
                if key in raw_module_info:
                    module_config[key] = raw_module_info[key]

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
            self.check_for_custom_generators(module_info)

            # Connect the module to the package
            module_info.package_info = self.package_info
            self.package_info.module_info_collection.append(module_info)

            # Parse the class data
            if not module_config["use_all_classes"]:
                if module_config["classes"]:
                    for raw_class_info in module_config["classes"]:
                        # Get class config from the raw class info
                        class_config = {"name_override": None, "source_file": None}
                        class_config.update(global_config)

                        for key in class_config.keys():
                            if key in raw_class_info:
                                class_config[key] = raw_class_info[key]

                        # Create the CppClassInfo object from the class config dict
                        class_info = CppClassInfo(raw_class_info["name"], class_config)
                        self.check_for_custom_generators(class_info)

                        # Connect the class to the module
                        class_info.module_info = module_info
                        module_info.class_info_collection.append(class_info)

            # Parse the free function data
            if not module_config["use_all_free_functions"]:
                if module_config["free_functions"]:
                    for raw_free_function_info in module_config["free_functions"]:
                        # Get free function config from the raw free function info
                        free_function_config = {
                            "name_override": None,
                            "source_file": None,
                        }
                        free_function_config.update(global_config)

                        for key in free_function_config.keys():
                            if key in raw_free_function_info:
                                free_function_config[key] = raw_free_function_info[key]

                        # Create the CppFreeFunctionInfo object from the free function config dict
                        free_function_info = CppFreeFunctionInfo(
                            free_function_config["name"], free_function_config
                        )

                        # Connect the free function to the module
                        free_function_info.module_info = module_info
                        module_info.free_function_info_collection.append(
                            free_function_info
                        )

            # Parse the variable data
            if not module_config["use_all_variables"]:
                for raw_variable_info in module_config["variables"]:
                    # Get variable config from the raw variable info
                    variable_config = {"name_override": None, "source_file": None}
                    variable_config.update(global_config)

                    for key in variable_config.keys():
                        if key in raw_variable_info:
                            variable_config[key] = raw_variable_info[key]

                    # Create the CppFreeFunctionInfo object from the variable config dict
                    variable_info = CppFreeFunctionInfo(
                        variable_config["name"], variable_config
                    )

                    # Connect the variable to the module
                    variable_info.module_info = module_info
                    module_info.variable_info_collection.append(variable_info)

        return self.package_info
