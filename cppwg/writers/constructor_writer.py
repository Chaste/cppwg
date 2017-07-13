from pygccxml import declarations

import base_writer

class CppConsturctorWrapperWriter(base_writer.CppBaseWrapperWriter):

    """
    Manage addition of constructor wrapper code
    """

    def __init__(self, class_info, 
                 ctor_decl,
                 class_decl,
                 wrapper_templates,
                 class_short_name=None):
        
        super(CppConsturctorWrapperWriter, self).__init__(wrapper_templates)

        self.class_info = class_info
        self.ctor_decl = ctor_decl
        self.class_decl = class_decl

        self.class_short_name = class_short_name
        if self.class_short_name is None:
            self.class_short_name = self.class_decl.name

    def exclusion_critera(self):

        # Check for exclusions
        exclusion_args = self.class_info.hierarchy_attribute_gather('calldef_excludes')
        ctor_arg_exludes = self.class_info.hierarchy_attribute_gather('constructor_arg_type_excludes')
            
        for eachArg in self.ctor_decl.argument_types:
            if eachArg.decl_string.replace(" ", "") in exclusion_args:
                return True

            for eachExclude in ctor_arg_exludes:
                if eachExclude in eachArg.decl_string:
                    return True

        for eachArg in self.ctor_decl.argument_types:
            if "iterator" in eachArg.decl_string.lower():
                return True

        if self.ctor_decl.parent != self.class_decl:
            return True

        if self.ctor_decl.is_artificial:
            return True

        return False

    def add_self(self, output_string):

        if self.exclusion_critera():
            return output_string

        output_string += " "*8 + '.def(py::init<'
        num_arg_types = len(self.ctor_decl.argument_types)
        for idx, eachArg in enumerate(self.ctor_decl.argument_types):
            output_string += eachArg.decl_string
            if idx < num_arg_types-1:
                output_string += ", "
        output_string += ' >()'

        default_args = ""
        if not self.default_arg_exclusion_criteria():
            for eachArg in self.ctor_decl.arguments:
                default_args += ', py::arg("{}")'.format(eachArg.name)
                if eachArg.default_value is not None:
                    default_args += ' = ' + eachArg.default_value
        output_string += default_args + ')\n'
        return output_string
