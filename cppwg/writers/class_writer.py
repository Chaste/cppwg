import collections
from pygccxml import declarations

import method_writer
import constructor_writer


class CppClassWrapperWriter():

    """
    This class generates wrapper code for Cpp classes
    """

    def __init__(self, class_info, wrapper_templates):

        self.hpp_string = ""
        self.cpp_string = ""
        self.class_info = class_info
        self.class_decls = []
        self.exposed_class_full_names = []
        self.class_full_names = self.class_info.get_full_names()
        self.class_short_names = self.class_info.get_short_names()
        self.has_shared_ptr = True
        self.exclusion_args = []
        self.is_abstract = False
        self.smart_ptr_handle = ""
        self.wrapper_templates = wrapper_templates
        self.tidy_replacements = collections.OrderedDict([(", ", "_"), ("<", ""), 
                                                          (">", ""), ("::", "_"), 
                                                          ("*", "Ptr"), ("&", "Ref"),
                                                          ("const", "")])

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

    def tidy_name(self, name):

        for key, value in self.tidy_replacements.items():
            name = name.replace(key, value)
        return name.replace(" ", "")

    def add_hpp(self, class_short_name):

        wrapper_dict = {'class_short_name': class_short_name}
        self.hpp_string += self.wrapper_templates['class_hpp_header'].format(**wrapper_dict)

    def add_cpp_header(self, class_full_name, class_short_name):

        header = "wrapper_header_collection"
#         if self.class_info.full_path is None:
#             header = "wrapper_header_collection"
#         else:
#             header = os.path.basename(self.class_info.full_path).split(".")[0]

        smart_ptr_handle = ""
        if self.smart_ptr_handle != "":
            smart_ptr_template = self.wrapper_templates["smart_pointer_holder"]
            smart_ptr_handle = smart_ptr_template.format(self.smart_ptr_handle)

        header_dict = {'wrapper_header_collection': header,
                       'class_short_name': class_short_name,
                       'class_full_name': class_full_name,
                       'smart_ptr_handle': smart_ptr_handle}
        header_string = self.wrapper_templates["class_cpp_header"].format(**header_dict)
        self.cpp_string += header_string

    def add_virtual_overides(self, class_decl, short_class_name):

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
                writer = constructor_writer.CppMethodWrapperWriter(class_decl, 
                                                               eachMethod,
                                                               self.wrapper_templates,
                                                               short_class_name,
                                                               self.exclusion_args)
                self.cpp_string = writer.add_override(self.cpp_string)
            self.cpp_string += "\n};\n"
        return needs_override

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

            # Define any virtual function overloads
            needs_overrides = self.add_virtual_overides(class_decl, short_name)

            # Add overrides if needed
            overrides_string = ""
            if needs_overrides:
                overrides_string = ', ' + short_name + '_Overloads'

            # Add smart ptr support if needed
            ptr_support = ""
            if self.has_shared_ptr and self.smart_ptr_handle != "":
                ptr_support = ', ' + self.smart_ptr_handle + '<' + short_name + ' > '

            # Add base classes if needed
            bases = ""
            for eachBase in class_decl.bases:
                exposed = eachBase.related_class.name in self.exposed_class_full_names
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
            if not self.is_abstract and not class_decl.is_abstract:
                query = declarations.access_type_matcher_t('public')
                for eachConstructor in class_decl.constructors(function=query,
                                                               allow_empty=True):
                    writer = constructor_writer.CppConsturctorWrapperWriter(class_decl, 
                                                               eachConstructor,
                                                               self.wrapper_templates,
                                                               short_name,
                                                               self.exclusion_args,
                                                               self.class_info.constructor_arg_type_excludes)
                    self.cpp_string = writer.add_self(self.cpp_string)

            # Add public member functions
            query = declarations.access_type_matcher_t('public')
            for eachMemberFunction in class_decl.member_functions(function=query,
                                                                  allow_empty=True):
                exlcuded = False
                if self.class_info.excluded_methods is not None:
                    exlcuded = (eachMemberFunction.name in
                                self.class_info.excluded_methods)
                if not exlcuded:
                    writer = method_writer.CppMethodWrapperWriter(class_decl, 
                                                               eachMemberFunction,
                                                               self.wrapper_templates,
                                                               short_name,
                                                               self.exclusion_args)
                    self.cpp_string = writer.add_self(self.cpp_string)

            # Close the class definition
            self.cpp_string += '    ;\n}\n'

            # Set up the hpp
            self.add_hpp(short_name)

            # Do the write
            self.write_files(work_dir, short_name)

