import os
import importlib
import logging
import yaml

from typing import Any, Optional

import cppwg.templates.custom

from cppwg.input.base_info import BaseInfo
from cppwg.input.class_info import CppClassInfo
from cppwg.input.free_function_info import CppFreeFunctionInfo
from cppwg.input.module_info import ModuleInfo
from cppwg.input.package_info import PackageInfo

from cppwg.utils import utils


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
            "CPPWG_SOURCEROOT", self.source_root
        )
        filepath = os.path.realpath(filepath)

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

        custom_module = importlib.machinery.SourceFileLoader(
            module_name, filepath
        ).load_module()

        # Get the custom generator class from the loaded module.
        # Note: The custom generator class name must match the filename.
        CustomGeneratorClass: cppwg.templates.custom.Custom = getattr(
            custom_module, class_name
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

        # Parse module data
        for eachModule in self.raw_package_info["modules"]:
            module_defaults = {
                "name": "cppwg_module",
                "source_locations": None,
                "classes": [],
                "free_functions": [],
                "variables": [],
                "use_all_classes": False,
                "use_all_free_functions": False,
            }
            module_defaults.update(global_config)

            for key in module_defaults.keys():
                if key in eachModule:
                    module_defaults[key] = eachModule[key]

            # Do classes
            class_info_collection = []
            module_defaults["use_all_classes"] = utils.is_option_ALL(
                "classes", module_defaults
            )
            if not module_defaults["use_all_classes"]:
                if module_defaults["classes"] is not None:
                    for eachClass in module_defaults["classes"]:
                        class_defaults = {"name_override": None, "source_file": None}
                        class_defaults.update(global_config)

                        for key in class_defaults.keys():
                            if key in eachClass:
                                class_defaults[key] = eachClass[key]
                        class_info = CppClassInfo(eachClass["name"], class_defaults)
                        self.check_for_custom_generators(class_info)
                        class_info_collection.append(class_info)

            # Do functions
            function_info_collection = []
            module_defaults["use_all_free_functions"] = utils.is_option_ALL(
                "free_functions", module_defaults
            )
            if not module_defaults["use_all_free_functions"]:
                if module_defaults["free_functions"] is not None:
                    for _ in module_defaults["free_functions"]:
                        ff_defaults = {"name_override": None, "source_file": None}
                        ff_defaults.update(global_config)
                        function_info = CppFreeFunctionInfo(
                            ff_defaults["name"], ff_defaults
                        )
                        function_info_collection.append(function_info)

            variable_info_collection = []
            use_all_variables = utils.is_option_ALL("variables", module_defaults)
            if not use_all_variables:
                for _ in module_defaults["variables"]:
                    variable_defaults = {"name_override": None, "source_file": None}
                    variable_defaults.update(global_config)
                    variable_info = CppFreeFunctionInfo(
                        variable_defaults["name"], variable_defaults
                    )
                    variable_info_collection.append(variable_info)

            module_info = ModuleInfo(module_defaults["name"], module_defaults)

            module_info.class_info_collection = class_info_collection
            for class_info in module_info.class_info_collection:
                class_info.module_info = module_info

            module_info.free_function_info_collection = function_info_collection
            for free_function_info in module_info.free_function_info_collection:
                free_function_info.module_info = module_info

            module_info.variable_info_collection = variable_info_collection
            for variable_info in module_info.variable_info_collection:
                variable_info.module_info = module_info

            self.package_info.module_info_collection.append(module_info)
            module_info.package_info = self.package_info

            self.check_for_custom_generators(module_info)

        return self.package_info
