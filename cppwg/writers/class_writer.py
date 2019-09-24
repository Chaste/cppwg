import ntpath

from pygccxml import declarations

from cppwg.writers import base_writer
from cppwg.writers import method_writer
from cppwg.writers import constructor_writer


class CppClassWrapperWriter(base_writer.CppBaseWrapperWriter):

    """
    This class generates wrapper code for Cpp classes
    """

    def __init__(self, class_info, wrapper_templates):
        
        super(CppClassWrapperWriter, self).__init__(wrapper_templates)

        self.hpp_string = ""
        self.cpp_string = ""
        self.class_info = class_info
        self.class_decls = []
        self.exposed_class_full_names = []
        self.class_full_names = self.class_info.get_full_names()
        self.class_short_names = self.class_info.get_short_names()
        self.has_shared_ptr = True
        self.is_abstract = False
        
        if(len(self.class_full_names) != len(self.class_short_names)):
            message = 'Full and short name lists should be the same length'
            raise ValueError(message)

    def write_files(self, work_dir, class_short_name):

        """
        Write the hpp and cpp wrapper codes to file
        """

        path = work_dir + "/" + class_short_name
        hpp_file = open(path + ".cppwg.hpp", "w")
        hpp_file.write(self.hpp_string)
        hpp_file.close()

        cpp_file = open(path + ".cppwg.cpp", "w")
        cpp_file.write(self.cpp_string)
        cpp_file.close()

    def add_hpp(self, class_short_name):
        
        """
        Add the class wrapper hpp file 
        """

        wrapper_dict = {'class_short_name': class_short_name}
        self.hpp_string += self.wrapper_templates['class_hpp_header'].format(**wrapper_dict)

    def add_cpp_header(self, class_full_name, class_short_name):
        
        """
        Add the 'top' of the class wrapper cpp file
        """

        header = "wrapper_header_collection"
        
        # Check for custom smart pointers
        smart_ptr_handle = ""
        smart_pointer_handle = self.class_info.hierarchy_attribute('smart_ptr_type')
        if smart_pointer_handle != None:
            smart_ptr_template = self.wrapper_templates["smart_pointer_holder"]
            smart_ptr_handle = "\n" + smart_ptr_template.format(smart_pointer_handle) + ";"

        header_dict = {'wrapper_header_collection': header,
                       'class_short_name': class_short_name,
                       'class_full_name': class_full_name,
                       'smart_ptr_handle': smart_ptr_handle,
                       'includes': '#include "' + header +'.hpp"\n'}
        extra_include_string = ""
        common_include_file = self.class_info.hierarchy_attribute('common_include_file')
        
        source_includes = []
        source_includes = self.class_info.hierarchy_attribute_gather('source_includes')

        if not common_include_file:
            for eachInclude in source_includes:
                if eachInclude[0] != "<":
                    extra_include_string += '#include "' + eachInclude +'"\n'
                else:
                    extra_include_string += '#include ' + eachInclude +'\n'
            if self.class_info.source_file is not None:
                extra_include_string += '#include "' + self.class_info.source_file +'"\n'                       
            else:
                include_name = ntpath.basename(self.class_info.decl.location.file_name)
                extra_include_string += '#include "' + include_name +'"\n'    
            header_dict['includes'] = extra_include_string

        header_string = self.wrapper_templates["class_cpp_header"].format(**header_dict)
        self.cpp_string += header_string
        
        for eachLine in self.class_info.prefix_code:
            self.cpp_string += eachLine + "\n"
            
        # Any custom generators
        if self.class_info.custom_generator is not None:
            self.cpp_string += self.class_info.custom_generator.get_class_cpp_pre_code(class_short_name)

    def add_virtual_overides(self, class_decl, short_class_name):
        
        """
        Virtual over-rides if neeeded
        """

        # Identify any methods needing over-rides, i.e. any that are virtual
        # here or in a parent.
        methods_needing_override = []
        return_types = []
        for eachMemberFunction in class_decl.member_functions(allow_empty=True):
            is_pure_virtual = eachMemberFunction.virtuality == "pure virtual"
            is_virtual = eachMemberFunction.virtuality == "virtual"
            if is_pure_virtual or is_virtual:
                methods_needing_override.append(eachMemberFunction)
                return_types.append(eachMemberFunction.return_type.decl_string)
            if is_pure_virtual:
                self.is_abstract = True

        for eachReturnString in return_types:
            if eachReturnString != self.tidy_name(eachReturnString):
                typdef_string = "typedef {full_name} {tidy_name};\n"
                typdef_dict = {'full_name': eachReturnString,
                               'tidy_name': self.tidy_name(eachReturnString)}
                self.cpp_string += typdef_string.format(**typdef_dict)
        self.cpp_string += "\n"

        needs_override = len(methods_needing_override) > 0
        if needs_override:
            over_ride_dict = {'class_short_name': short_class_name,
                              'class_base_name': self.class_info.name}
            override_template = self.wrapper_templates['class_virtual_override_header']
            self.cpp_string += override_template.format(**over_ride_dict)

            for eachMethod in methods_needing_override:
                writer = method_writer.CppMethodWrapperWriter(self.class_info, 
                                                               eachMethod,
                                                               class_decl,
                                                               self.wrapper_templates,
                                                               short_class_name)
                self.cpp_string = writer.add_override(self.cpp_string)
            self.cpp_string += "\n};\n"
        return methods_needing_override

    def write(self, work_dir):

        if(len(self.class_decls) != len(self.class_full_names)):
            message = 'Not enough class decls added to do write.'
            raise ValueError(message)

        for idx, full_name in enumerate(self.class_full_names):
            short_name = self.class_short_names[idx]
            class_decl = self.class_decls[idx]
            self.hpp_string = ""
            self.cpp_string = ""

            # Add the cpp file header
            self.add_cpp_header(full_name, short_name)
            
            # Check for struct-enum pattern
            if declarations.is_struct(class_decl):
                enums = class_decl.enumerations(allow_empty=True)
                if len(enums)==1:
                    replacements = {'class': class_decl.name, 'enum': enums[0].name}
                    self.cpp_string += 'void register_{class}_class(py::module &m){{\n'.format(**replacements)
                    self.cpp_string += '    py::class_<{class}> myclass(m, "{class}");\n'.format(**replacements)
                    self.cpp_string += '    py::enum_<{class}::{enum}>(myclass, "{enum}")\n'.format(**replacements)
                    for eachval in enums[0].values:
                        replacements = {'class': class_decl.name,
                                        'enum': enums[0].name,
                                        'val': eachval[0]}
                        self.cpp_string += '        .value("{val}", {class}::{enum}::{val})\n'.format(**replacements)
                    self.cpp_string += "    .export_values();\n}\n"
                    
                    # Set up the hpp
                    self.add_hpp(short_name)
        
                    # Do the write
                    self.write_files(work_dir, short_name)
                continue

            # Define any virtual function overloads
            methods_needing_override = self.add_virtual_overides(class_decl, short_name)

            # Add overrides if needed
            overrides_string = ""
            if len(methods_needing_override)>0:
                overrides_string = ', ' + short_name + '_Overloads'

            # Add smart ptr support if needed
            smart_pointer_handle = self.class_info.hierarchy_attribute('smart_ptr_type')
            ptr_support = ""
            if self.has_shared_ptr and smart_pointer_handle is not None:
                ptr_support = ', ' + smart_pointer_handle + '<' + short_name + ' > '

            # Add base classes if needed
            bases = ""
            for eachBase in class_decl.bases:
                cleaned_base = eachBase.related_class.name.replace(" ","")
                exposed = any(cleaned_base in t.replace(" ","") for t in self.exposed_class_full_names)
                public = not eachBase.access_type == "private"
                if exposed and public:
                    bases += ', ' + eachBase.related_class.name + " "

            # Add the class refistration
            class_definition_dict = {'short_name': short_name,
                                     'overrides_string': overrides_string,
                                     'ptr_support': ptr_support,
                                     'bases': bases}
            class_definition_template = self.wrapper_templates["class_definition"]
            self.cpp_string += class_definition_template.format(**class_definition_dict)

            # Add constructors
            #if not self.is_abstract and not class_decl.is_abstract:
            # No constructors for classes with private pure virtual methods!
            ppv_class = False
            for eachMemberFunction in class_decl.member_functions(allow_empty=True):
                if eachMemberFunction.virtuality == "pure virtual" and eachMemberFunction.access_type == "private":
                    ppv_class = True
                    break
                
            if not ppv_class:
                query = declarations.access_type_matcher_t('public')
                for eachConstructor in class_decl.constructors(function=query,
                                                               allow_empty=True):
                    writer = constructor_writer.CppConsturctorWrapperWriter(self.class_info, 
                                                               eachConstructor,
                                                               class_decl,
                                                               self.wrapper_templates,
                                                               short_name)
                    self.cpp_string = writer.add_self(self.cpp_string)

            # Add public member functions
            query = declarations.access_type_matcher_t('public')
            for eachMemberFunction in class_decl.member_functions(function=query, allow_empty=True):
                exlcuded = False
                if self.class_info.excluded_methods is not None:
                    exlcuded = (eachMemberFunction.name in self.class_info.excluded_methods)
                if not exlcuded:
                    writer = method_writer.CppMethodWrapperWriter(self.class_info, 
                                                                  eachMemberFunction,
                                                                  class_decl,
                                                                  self.wrapper_templates,
                                                                  short_name)
                    self.cpp_string = writer.add_self(self.cpp_string)
                    
            # Any custom generators
            if self.class_info.custom_generator is not None:
                self.cpp_string += self.class_info.custom_generator.get_class_cpp_def_code(short_name)

            # Close the class definition
            self.cpp_string += '    ;\n}\n'

            # Set up the hpp
            self.add_hpp(short_name)

            # Do the write
            self.write_files(work_dir, short_name)
