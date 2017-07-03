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

import os
from pygccxml import parser, declarations
import pygccxml.declarations.dependencies

import free_function_writer
import class_writer


class CppModuleWrapperWriter():

    def __init__(self, global_ns, source_ns, package_name,
                 module_info, wrapper_templates, wrapper_root,
                 package_license=None):

        self.global_ns = global_ns
        self.source_ns = source_ns
        self.module_info = module_info
        self.wrapper_root = wrapper_root
        self.package_name = package_name
        self.exposed_class_full_names = []
        self.wrapper_templates = wrapper_templates
        self.license = package_license

        self.exposed_class_full_names = []

    def check_class_eligibility(self):

        for eachClass in self.module_info.classes:
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

    def generate_main_cpp(self):

        # Generate the main cpp file
        module_name = self.module_info.name
        full_module_name = "_" + self.package_name + "_" + module_name

        cpp_string = ""
        cpp_string += '#include <pybind11/pybind11.h>\n'
        cpp_string += '#include "wrapper_header_collection.hpp"\n'

        # Add includes
        if self.module_info.class_info is not None:
            for eachClass in self.module_info.class_info:
                for short_name in eachClass.get_short_names():
                    cpp_string += '#include "' + short_name + '.cppwg.hpp"\n'
        cpp_string += '\nnamespace py = pybind11;\n\n'
        cpp_string += 'PYBIND11_MODULE(' + full_module_name + ', m)\n{\n'

        # Add free functions
        if self.module_info.free_function_info is not None:
            for eachFunction in self.module_info.free_function_info:
                writer = free_function_writer.CppFreeFunctionWrapperWriter(eachFunction.decl,
                                                                           self.wrapper_templates)
                cpp_string = writer.add_self(cpp_string)

        # Add viable classes
        if self.module_info.class_info is not None:
            for eachClass in self.module_info.class_info:
                for short_name in eachClass.get_short_names():
                    cpp_string += '    register_' + short_name + '_class(m);\n'

        output_dir = self.wrapper_root + "/" + self.module_info.name + "/"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        main_cpp_file = open(output_dir +
                             self.module_info.name + ".main.cpp", "w")
        main_cpp_file.write(cpp_string + '}\n')
        main_cpp_file.close()

    def get_class_writer(self, class_info):

        return class_writer.CppClassWrapperWriter(class_info,
                                                  self.wrapper_templates)

    def write(self):

        print 'Generating Wrapper Code for: ' + self.module_info.name + ' Module.'

        # self.check_class_eligibility()
        self.generate_main_cpp()

        # Generate class files
        for eachClassInfo in self.module_info.class_info:
            self.exposed_class_full_names.extend(eachClassInfo.get_full_names())

        for eachClassInfo in self.module_info.class_info:

            print 'Generating Wrapper Code for: ' + eachClassInfo.name + ' Class.'

            class_writer = self.get_class_writer(eachClassInfo)
            class_writer.exposed_class_full_names = self.exposed_class_full_names

            for fullName in eachClassInfo.get_full_names():
                class_decl = self.source_ns.class_(fullName)
#                     print "Class: ", eachClass.name,
#                     print "Deps:"
#                     for eachDep in declarations.dependencies.get_dependencies_from_decl(class_decl):
#                         print eachDep.declaration.name
                class_writer.class_decls.append(class_decl)
            class_writer.write(self.wrapper_root + "/" + self.module_info.name + "/")
