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


class CppSourceParser():

    def __init__(self, source_root,
                 wrapper_header_collection,
                 castxml_binary,
                 includes,
                 ):

        self.source_root = source_root
        self.wrapper_header_collection = wrapper_header_collection
        self.castxml_binary = castxml_binary
        self.includes = includes
        self.global_ns = None
        self.source_ns = None

    def parse(self):

        xml_generator_config = parser.xml_generator_configuration_t(xml_generator_path=self.castxml_binary, 
                                                                    xml_generator="castxml",
                                                                    cflags="-std=c++11",
                                                                    include_paths=self.includes)

        print "INFO: Parsing Code"
        decls = parser.parse([self.wrapper_header_collection], xml_generator_config,
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