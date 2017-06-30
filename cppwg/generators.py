import os
import logging
import fnmatch

from cppwg.input.module_info import CppModuleInfo
from cppwg.parsers.package_info import PackageInfoParser
from cppwg.writers.header_collection_writer import CppHeaderCollectionWriter
from cppwg.parsers.source_parser import CppSourceParser
from cppwg.writers.module_writer import CppModuleWrapperWriter

class CppWrapperGenerator():

    def __init__(self, source_root, includes=None, 
                 wrapper_root=None,
                 castxml_binary='castxml',
                 package_info_path='package_info.yaml'):

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        self.source_root = source_root
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

    def generate_wrapper(self):

        # If there is an input file, parse it
        if self.package_info_path is not None:
            info_parser = PackageInfoParser(self.package_info_path)
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

        # Write the modules
        #for eachModule in self.modules:
            #module_writer = CppModuleWrapperWriter()
            #module_writer.write()
