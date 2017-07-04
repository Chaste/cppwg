import yaml

from cppwg.input.module_info import CppModuleInfo
from cppwg.input.class_info import CppClassInfo
from cppwg.input.free_function_info import CppFreeFunctionInfo

class PackageInfoParser():

    def __init__(self, file_path, source_root):

        self.file_path = file_path
        self.raw_info = {}
        self.package_name = "cppwg_package"
        self.modules = []
        self.source_root = source_root

    def parse(self):

        with open(self.file_path, 'r') as myfile:
            data = myfile.read()

        self.raw_info = yaml.load(data)

        # Parse package data
        package_defaults = {'name': 'cppwg_package',
                            'global_includes': [],
                            'smart_ptr_type': None,
                            'common_include_file': True,
                            'global_calldef_excludes': None,
                            'global_template_substitutions': [],
                            'global_pointer_call_policy': None,
                            'global_reference_call_policy': None}
        for eachEntry in package_defaults.keys():
            if eachEntry in self.raw_info:
                package_defaults[eachEntry] = self.raw_info[eachEntry]

        self.package_name = package_defaults['name']
        is_string = isinstance(package_defaults['common_include_file'], basestring)
        if is_string and package_defaults['common_include_file'].strip() == "OFF":
            package_defaults['common_include_file'] = False

        # Parse module data
        for eachModule in self.raw_info['modules']:
            defaults = {'name':'cppwg_module',
                        'source_locations': None,
                        'classes': [],
                        'free_functions': []}
            for eachEntry in defaults.keys():
                if eachEntry in eachModule:
                    defaults[eachEntry] = eachModule[eachEntry]

            class_info_collection = []
            use_all_classes = False
            is_string = isinstance(defaults['classes'], basestring)
            if is_string and defaults['classes'].upper() == "CPPWG_ALL":
                use_all_classes = True
            else:
                for eachClass in defaults['classes']:
                    class_defaults = {'excluded_methods': [],
                                'excluded_variables': [],
                                'name_override': None,
                                'pointer_return_methods': [],
                                'extra_includes': [],
                                'source_file': None,
                                'constructor_arg_type_excludes': []}
                    for eachEntry in class_defaults.keys():
                        if eachEntry in eachClass:
                            class_defaults[eachEntry] = eachClass[eachEntry]
                    class_info = CppClassInfo(eachClass['name'],
                                              excluded_methods=class_defaults['excluded_methods'],
                                              excluded_variables=class_defaults['excluded_variables'],
                                              name_override=class_defaults['name_override'],
                                              pointer_return_methods=class_defaults['pointer_return_methods'],
                                              extra_includes=class_defaults['extra_includes'],
                                              source_file=class_defaults['source_file'],
                                              constructor_arg_type_excludes=class_defaults['constructor_arg_type_excludes'])
                    class_info.constructor_arg_type_excludes.extend(package_defaults['global_calldef_excludes'])
                    class_info_collection.append(class_info)

            function_info_collection = []
            use_all_functions = False
            is_string = isinstance(defaults['free_functions'], basestring)
            if is_string and defaults['free_functions'].upper() == "CPPWG_ALL":
                use_all_functions = True
            else:
                for eachFunction in defaults['free_functions']:
                    function_info = CppFreeFunctionInfo(eachFunction['name'])
                    function_info_collection.append(function_info)

            self.modules.append(CppModuleInfo(defaults['name'],
                                              self.source_root,
                                              defaults['source_locations'],
                                              class_info_collection,
                                              function_info_collection,
                                              use_all_classes,
                                              use_all_functions,
                                              smart_ptr_type=package_defaults['smart_ptr_type'],
                                              global_includes=package_defaults['global_includes'],
                                              common_include_file=package_defaults['common_include_file'],
                                              global_calldef_excludes=package_defaults['global_calldef_excludes'],
                                              global_template_substitutions=package_defaults['global_template_substitutions'],
                                              global_pointer_call_policy=package_defaults['global_pointer_call_policy'],
                                              global_reference_call_policy=package_defaults['global_reference_call_policy'],))
