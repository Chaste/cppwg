import collections
from pygccxml import declarations


class CppConsturctorWrapperWriter():

    """
    Manage addition of constructor wrapper code
    """

    def __init__(self, class_decl, ctor_decl,
                 wrapper_templates,
                 class_short_name=None,
                 exclusion_args=None,
                 ctor_arg_exludes=None):

        self.class_decl = class_decl
        self.ctor_decl = ctor_decl
        self.wrapper_templates = wrapper_templates

        self.class_short_name = class_short_name
        if self.class_short_name is None:
            self.class_short_name = self.class_decl.name

        self.exclusion_args = exclusion_args
        if self.exclusion_args is None:
            self.exclusion_args = []

        self.ctor_arg_exludes = ctor_arg_exludes
        if self.ctor_arg_exludes is None:
            self.ctor_arg_exludes = []

    def exclusion_critera(self):

        # Check for exclusions
        for eachArg in self.ctor_decl.argument_types:
            if eachArg.decl_string.replace(" ", "") in self.exclusion_args:
                return True

            for eachExclude in self.ctor_arg_exludes:
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
        output_string += ' >(''))\n'
        return output_string
