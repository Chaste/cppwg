import os
import imp
import yaml

from typing import Optional

from cppwg.input.class_info import CppClassInfo
from cppwg.input.free_function_info import CppFreeFunctionInfo
from cppwg.input.module_info import ModuleInfo
from cppwg.input.package_info import PackageInfo


class PackageInfoParser:

    def __init__(self, input_file: str, source_root: str):
        """
        Args:

            input_file (str): The path to the package info yaml file.
            source_root (str): The root directory of the C++ source code.
        """

        self.input_file: str = input_file
        self.source_root: str = source_root

        # Raw info from the yaml file
        self.raw_info: dict = {}

        # The parsed package info
        self.package_info: Optional[PackageInfo] = None

    def substitute_bool_string(self, option, input_dict, on_string="ON", off_string="OFF"):

        is_string = isinstance(input_dict[option], str)
        if is_string and input_dict[option].strip().upper() == off_string:
            input_dict[option] = False   
        elif is_string and input_dict[option].strip().upper() == on_string:
            input_dict[option] = True  

    def is_option_ALL(self, option, input_dict, check_string = "CPPWG_ALL"): 

        is_string = isinstance(input_dict[option], str)
        return is_string and input_dict[option].upper() == check_string

    def check_for_custom_generators(self, feature_info):

        # Replace source root if needed
        if feature_info.custom_generator is not None:
            path = feature_info.custom_generator.replace("CPPWG_SOURCEROOT", self.source_root)
            path = os.path.realpath(path)
            print (feature_info.name, path)
            if os.path.isfile(path):
                module_name = os.path.basename(path).split(".")[0]
                custom_module = imp.load_source(os.path.splitext(path)[0], path)
                feature_info.custom_generator = getattr(custom_module, module_name)()

    def parse(self):
        """
        Parse the package info yaml file to extract information about the 
        package, modules, classes, and free functions.
        """

        with open(self.input_file, "r") as input_file:
            self.raw_info = yaml.safe_load(input_file)

        global_config = {
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

        # Parse package data
        package_config = {
            "name": "cppwg_package",
            "common_include_file": True,
            "source_hpp_patterns": ["*.hpp"],
        }
        package_config.update(global_config)

        for key in package_config.keys():
            if key in self.raw_info:
                package_config[key] = self.raw_info[key]

        self.package_info = PackageInfo(
            package_config["name"], self.source_root, package_config
        )
        self.check_for_custom_generators(self.package_info)
        # exit()
        # Parse module data
        for eachModule in self.raw_info['modules']:
            module_defaults = {'name':'cppwg_module',
                               'source_locations': None,
                               'classes': [],
                               'free_functions': [],
                               'variables': [],
                               'use_all_classes': False,
                               'use_all_free_functions': False}
            module_defaults.update(global_config)

            for key in module_defaults.keys():
                if key in eachModule:
                    module_defaults[key] = eachModule[key]

            # Do classes
            class_info_collection = []
            module_defaults['use_all_classes'] = self.is_option_ALL('classes', module_defaults)
            if not module_defaults['use_all_classes']:
                if module_defaults['classes'] is not None:
                    for eachClass in module_defaults['classes']:
                        class_defaults = { 'name_override': None,
                                           'source_file': None}
                        class_defaults.update(global_config)

                        for key in class_defaults.keys():
                            if key in eachClass:
                                class_defaults[key] = eachClass[key]
                        class_info = CppClassInfo(eachClass['name'], class_defaults)
                        self.check_for_custom_generators(class_info)
                        class_info_collection.append(class_info)

            # Do functions
            function_info_collection = []
            module_defaults['use_all_free_functions'] = self.is_option_ALL('free_functions',
                                                                            module_defaults)
            if not module_defaults['use_all_free_functions']:
                if module_defaults['free_functions'] is not None:
                    for _ in module_defaults['free_functions']:
                        ff_defaults = { 'name_override': None,
                                        'source_file': None}
                        ff_defaults.update(global_config)                    
                        function_info = CppFreeFunctionInfo(ff_defaults['name'], ff_defaults)
                        function_info_collection.append(function_info)

            variable_info_collection = []
            use_all_variables = self.is_option_ALL('variables', module_defaults)
            if not use_all_variables:
                for _ in module_defaults['variables']:
                    variable_defaults = { 'name_override': None,
                                         'source_file': None}
                    variable_defaults.update(global_config)                    
                    variable_info = CppFreeFunctionInfo(variable_defaults['name'], variable_defaults)
                    variable_info_collection.append(variable_info)            

            module_info = ModuleInfo(module_defaults['name'], module_defaults)

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
