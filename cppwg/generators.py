import os
import logging
import fnmatch

from cppwg.input.module_info import CppModuleInfo
from cppwg.input.free_function_info import CppFreeFunctionInfo
from cppwg.input.class_info import CppClassInfo
from cppwg.parsers.package_info import PackageInfoParser
from cppwg.writers.header_collection_writer import CppHeaderCollectionWriter
from cppwg.parsers.source_parser import CppSourceParser
from cppwg.writers.module_writer import CppModuleWrapperWriter

import cppwg.templates.pybind11_default as wrapper_templates


class CppWrapperGenerator():

    def __init__(self, source_root, includes=None, 
                 wrapper_root=None,
                 castxml_binary='castxml',
                 package_info_path='package_info.yaml'):

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        self.source_root = os.path.realpath(source_root)
        self.includes = includes
        self.wrapper_root = wrapper_root
        self.castxml_binary = castxml_binary
        self.package_info_path = package_info_path
        self.modules = []
        self.package_name = "cppwg_package"
        self.source_hpp_patterns = ["*.hpp"]
        self.source_hpp_files = []
        self.global_ns = None
        self.source_ns = None

        if self.wrapper_root is None:
            self.wrapper_root = self.source_root

        if self.includes is None:
            self.includes = [self.source_root]

        # If we suspect that a valid info file has not been supplied
        # fall back to the default behaviour
        path_is_default = (self.package_info_path == 'package_info.yaml')
        file_exists = os.path.exists(self.package_info_path)
        if path_is_default and (not file_exists):
            logger.info('YAML package info file not found. Using default info.')
            self.package_info_path = None

    def collect_source_hpp_files(self):

        for root, _, filenames in os.walk(self.source_root, followlinks=True):
            for pattern in self.source_hpp_patterns:
                for filename in fnmatch.filter(filenames, pattern):
                    self.source_hpp_files.append(os.path.join(root, filename))

    def generate_header_collection(self):

        header_collection_writer = CppHeaderCollectionWriter(self.source_root,
                                                             self.wrapper_root,
                                                             self.modules,
                                                             self.source_hpp_files,
                                                             self.package_name)
        header_collection_writer.write()
        header_collection_path = self.wrapper_root + "/"
        header_collection_path += header_collection_writer.header_file_name

        return header_collection_path

    def parse_header_collection(self, header_collection_path):

        source_parser = CppSourceParser(self.source_root,
                                        header_collection_path,
                                        self.castxml_binary,
                                        self.includes)
        source_parser.parse()
        self.global_ns = source_parser.global_ns
        self.source_ns = source_parser.source_ns

    def get_wrapper_template(self):
        return wrapper_templates.template_collection

    def generate_free_function_info(self):
        for eachModule in self.modules:
            if eachModule.using_all_free_functions():
                free_functions = self.source_ns.free_functions(allow_empty=True)
                for eachFunction in free_functions:
                    if eachModule.decl_in_source_path(eachFunction):
                        function_info = CppFreeFunctionInfo(eachFunction.name,
                                                            eachModule)
                        function_info.decl = eachFunction
                        if eachModule.free_function_info is not None:
                            eachModule.free_function_info.append(function_info)
                        else:
                            eachModule.free_function_info = [function_info]
            else:
                for eachFunction in eachModule.free_functions():
                    functions = self.source_ns.free_functions(eachFunction.name,
                                                              allow_empty=True)
                    if len(functions) == 1:
                        function_info = CppFreeFunctionInfo(functions[0].name,
                                                            eachModule)
                        function_info.decl = functions[0]
                        eachModule.function_info.append(function_info)

    def generate_class_info(self):
        for eachModule in self.modules:
            if eachModule.using_all_classes():
                classes = self.source_ns.classes(allow_empty=True)
                for eachClass in classes:
                    if eachModule.decl_in_source_path(eachClass):
                        class_info = CppClassInfo(eachClass.name,
                                                  eachModule)
                        class_info.decl = eachClass
                        eachModule.function_info.append(class_info)
            else:
                for eachClass in eachModule.classes():
                    classes = self.source_ns.classes(eachClass.name,
                                                              allow_empty=True)
                    if len(classes) == 1:
                        class_info = CppClassInfo(classes[0].name,
                                                            eachModule)
                        class_info.decl = classes[0]
                        eachModule.class_info.append(class_info)

    def generate_wrapper(self):

        # If there is an input file, parse it
        if self.package_info_path is not None:
            info_parser = PackageInfoParser(self.package_info_path, 
                                            self.source_root)
            info_parser.parse()
            self.modules = info_parser.modules
            self.package_name = info_parser.package_name
        else:
            self.modules.append(CppModuleInfo("cppwg_module"))

        # Generate a header collection
        self.collect_source_hpp_files()
        header_collection_path = self.generate_header_collection()

        # Parse the header collection
        self.parse_header_collection(header_collection_path)

        # Generate the Class and Free Function Info
        self.generate_free_function_info()

        self.generate_class_info()

        # Write the modules
        for eachModule in self.modules:
            module_writer = CppModuleWrapperWriter(self.global_ns,
                                                   self.source_ns,
                                                   self.package_name,
                                                   eachModule,
                                                   self.get_wrapper_template(),
                                                   self.wrapper_root)
            module_writer.write()
