#!/usr/bin/env python

"""Copyright (c) 2005-2017, University of Oxford.
All rights reserved.

University of Oxford means the Chancellor, Masters and Scholars of the
University of Oxford, having an administrative office at Wellington
Square, Oxford OX1 2JD, UK.

This file is part of cppwg.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
 * Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 * Neither the name of the University of Oxford nor the names of its
   contributors may be used to endorse or promote products derived from this
   software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
This scipt automatically generates Python bindings using a rule based approach
"""

from pygccxml import parser, declarations
import pygccxml.declarations.dependencies

import cppwg.templates.pybind11_default as wrapper_templates
import class_writer


class CppModuleWrapperWriter():

    def __init__(self, source_root, 
                 wrapper_root,
                 header_collection, 
                 castxml_binary, 
                 module_name, 
                 includes,
                 class_info_collection):

        self.license = ""
        self.source_root = source_root
        self.wrapper_root = wrapper_root
        self.header_collection = header_collection
        self.castxml_binary = castxml_binary
        self.module_name = module_name
        self.includes = includes
        self.global_ns = None
        self.source_ns = None
        self.wrapper_header_name = "wrapper_header_collection.hpp"
        self.class_info_collection = class_info_collection
        self.module_prefix = ""
        self.module_names = ["cppwg_module"]
        self.exposed_class_full_names = []
        self.wrapper_templates = wrapper_templates.template_collection
        self.license = ""

        for eachClassInfo in self.class_info_collection:
            self.exposed_class_full_names.extend(eachClassInfo.get_full_names())

    def parse_source_code(self):

        xml_generator_config = parser.xml_generator_configuration_t(xml_generator_path=self.castxml_binary, 
                                                                    xml_generator="castxml",
                                                                    cflags="-std=c++11",
                                                                    include_paths=self.includes)

        print "INFO: Parsing Code"
        decls = parser.parse([self.wrapper_root + "/" +
                              self.wrapper_header_name], xml_generator_config,
                             compilation_mode=parser.COMPILATION_MODE.ALL_AT_ONCE)

        # Get access to the global namespace
        self.global_ns = declarations.get_global_namespace(decls)

        # Clean decls to only include those for which file locations exist
        print "INFO: Cleaning Decls"
        query = declarations.custom_matcher_t(lambda decl: decl.location is not None)
        decls_loc_not_none = self.global_ns.decls(function=query)

        # Identify decls in our source tree
        source_decls = [decl for decl in decls_loc_not_none if self.source_root in decl.location.file_name]
        self.source_ns = declarations.namespace_t("source", source_decls)

        print "INFO: Optimizing Decls"
        self.source_ns.init_optimizer()

    def check_class_eligibility(self, module_name):

        for eachClass in self.class_info_collection:
            eachClass.include_in_this_module = True

            # Check if in module
            in_module = eachClass.component == module_name
            if eachClass.include_file_only or (not in_module):
                eachClass.include_in_this_module = False
                continue

            # Ensure declatation exists
            for fullName in eachClass.get_full_names():
                classes = self.source_ns.classes(fullName, allow_empty=True)
                if len(classes) == 0:
                    eachClass.include_in_this_module = False
                    break

    def generate_main_cpp(self, module_name):

        # Generate the main cpp file
        main_cpp_file = open(self.wrapper_root + "/" + module_name + "/" +
                             module_name + ".main.cpp", "w")
        main_cpp_file.write('#include <pybind11/pybind11.h>\n')

        # Add includes
        for eachClass in self.class_info_collection:
            if eachClass.include_in_this_module:
                for short_name in eachClass.get_short_names():
                    main_cpp_file.write('#include "' + short_name + '.cppwg.hpp"\n')
        main_cpp_file.write('\nnamespace py = pybind11;\n\n')
        main_cpp_file.write('PYBIND11_MODULE(' + self.module_prefix+module_name +
                            ', m)\n{\n')

        # Add viable classes
        for eachClass in self.class_info_collection:
            if eachClass.include_in_this_module:
                for short_name in eachClass.get_short_names():
                    main_cpp_file.write('register_' + short_name + '_class(m);\n')
        main_cpp_file.write('}\n')
        main_cpp_file.close()

    def get_class_writer(self, class_info):

        return class_writers.CppClassWrapperWriter(class_info,
                                                   self.wrapper_templates)

    def generate_wrappers(self):

        self.parse_source_code()

        possible_module_names = [self.module_name]
        if self.module_name == "All":
            possible_module_names = self.module_names

        for eachModule in possible_module_names:

            print 'Generating Wrapper Code for: ' + eachModule + ' Module.'

            self.check_class_eligibility(eachModule)
            self.generate_main_cpp(eachModule)

            # Generate class files
            for eachClass in self.class_info_collection:

                if not eachClass.include_in_this_module:
                    continue

                print 'Generating Wrapper Code for: ' + eachClass.name + ' Class.'

                class_writer = self.get_class_writer(eachClass)
                class_writer.exposed_class_full_names = self.exposed_class_full_names

                for fullName in eachClass.get_full_names():
                    class_decl = self.source_ns.class_(fullName)
#                     print "Class: ", eachClass.name,
#                     print "Deps:"
#                     for eachDep in declarations.dependencies.get_dependencies_from_decl(class_decl):
#                         print eachDep.declaration.name
                    class_writer.class_decls.append(class_decl)
                class_writer.write(self.wrapper_root + "/" + eachModule + "/")  
