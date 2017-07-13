#!/usr/bin/env python

"""
Generate the file classes_to_be_wrapped.hpp, which contains includes,
instantiation and naming typedefs for all classes that are to be
automatically wrapped.
"""

import os
import ntpath
import fnmatch


class CppHeaderCollectionWriter():

    """
    This class manages generation of the header collection file for
    parsing by CastXML
    """

    def __init__(self, package_info, wrapper_root):

        self.wrapper_root = wrapper_root
        self.package_info = package_info
        self.header_file_name = "wrapper_header_collection.hpp"
        self.hpp_string = ""
        self.class_dict = {}
        self.free_func_dict = {}

        for eachModule in self.package_info.module_info:
            for eachClassInfo in eachModule.class_info:
                self.class_dict[eachClassInfo.name] = eachClassInfo

            for eachFuncInfo in eachModule.free_function_info:
                self.free_func_dict[eachFuncInfo.name] = eachFuncInfo

    def add_custom_header_code(self):
        
        """
        Any custom header code goes here
        """

        pass

    def write_file(self):

        """
        The actual write
        """
        
        if not os.path.exists(self.wrapper_root + "/"):
            os.makedirs(self.wrapper_root + "/")
        file_path = self.wrapper_root + "/" + self.header_file_name
        hpp_file = open(file_path, 'w')
        hpp_file.write(self.hpp_string)
        hpp_file.close()

    def should_include_all(self):
        
        """
        Return whether all source files in the module source locs should be included
        """        

        for eachModule in self.package_info.module_info:
            if eachModule.use_all_classes or eachModule.use_all_free_functions:
                    return True
        return False

    def write(self):
        
        """
        Main method for generating the header file output string
        """

        hpp_header_dict = {'package_name': self.package_info.name}
        hpp_header_template = """\
#ifndef {package_name}_HEADERS_HPP_
#define {package_name}_HEADERS_HPP_

// Includes
"""
        self.hpp_string = hpp_header_template.format(**hpp_header_dict)

        # Now our own includes
        if self.should_include_all():
            for eachFile in self.package_info.source_hpp_files:
                include_name = ntpath.basename(eachFile)
                self.hpp_string += '#include "' + include_name + '"\n'
        else:
            for eachModule in self.package_info.module_info:
                for eachClassInfo in eachModule.class_info:
                    if eachClassInfo.source_file is not None:
                        self.hpp_string += '#include "' + eachClassInfo.source_file + '"\n'
                    elif eachClassInfo.source_file_full_path is not None:
                        include_name = ntpath.basename(eachClassInfo.source_file_full_path)
                        self.hpp_string += '#include "' + include_name + '"\n'
                for eachFuncInfo in eachModule.free_function_info:
                    if eachFuncInfo.source_file_full_path is not None:
                        include_name = ntpath.basename(eachFuncInfo.source_file_full_path)
                        self.hpp_string += '#include "' + include_name + '"\n'

        # Add the template instantiations
        self.hpp_string += "\n// Instantiate Template Classes \n"
        for eachModule in self.package_info.module_info:
            for eachClassInfo in eachModule.class_info:
                full_names = eachClassInfo.get_full_names()
                if len(full_names) == 1:
                    continue
                prefix = "template class "
                for eachTemplateName in full_names:
                    self.hpp_string += prefix + eachTemplateName + ";\n"

        # Add typdefs for nice naming
        self.hpp_string += "\n// Typedef for nicer naming\n"
        self.hpp_string += "namespace cppwg{ \n"
        for eachModule in self.package_info.module_info:
            for eachClassInfo in eachModule.class_info:
                full_names = eachClassInfo.get_full_names()
                if len(full_names) == 1:
                    continue
    
                short_names = eachClassInfo.get_short_names()
                for idx, eachTemplateName in enumerate(full_names):
                    short_name = short_names[idx]
                    typdef_prefix = "typedef " + eachTemplateName + " "
                    self.hpp_string += typdef_prefix + short_name + ";\n"
        self.hpp_string += "}\n"

        self.add_custom_header_code()
        self.hpp_string += "\n#endif // {}_HEADERS_HPP_\n".format(self.package_info.name)

        self.write_file()
