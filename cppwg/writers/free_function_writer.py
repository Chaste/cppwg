import collections


class CppFreeFunctionWrapperWriter():

    """
    Manage addition of free function wrapper code
    """

    def __init__(self, decl,
                 wrapper_templates,
                 exclusion_args=None):

        self.decl = decl
        self.wrapper_templates = wrapper_templates

        self.exclusion_args = exclusion_args
        if self.exclusion_args is None:
            self.exclusion_args = []

        self.tidy_replacements = collections.OrderedDict([(", ", "_"), ("<", ""), 
                                                          (">", ""), ("::", "_"), 
                                                          ("*", "Ptr"), ("&", "Ref"),
                                                          ("const", "")])

    def tidy_name(self, name):

        for key, value in self.tidy_replacements.items():
            name = name.replace(key, value)
        return name.replace(" ", "")

    def exclusion_critera(self):

        # Are any return types not wrappable
        return_type = self.decl.return_type.decl_string.replace(" ", "")
        if return_type in self.exclusion_args:
            return True

        # Are any arguements not wrappable
        for eachArg in self.decl.argument_types:
            arg_type = eachArg.decl_string.split()[0].replace(" ", "")
            if arg_type in self.exclusion_args:
                return True
        return False

    def default_arg_exclusion_criteria(self):

        return False

    def add_self(self, output_string):

        # Check for exclusions
        if self.exclusion_critera():
            return output_string

        # Which definition type
        def_adorn = ""

        # Get the arg signature
        arg_signature = ""
        num_arg_types = len(self.decl.argument_types)
        for idx, eachArg in enumerate(self.decl.argument_types):
            arg_signature += eachArg.decl_string
            if idx < num_arg_types-1:
                arg_signature += ", "

        # Default args
        default_args = ""
        if not self.default_arg_exclusion_criteria():
            for eachArg in self.decl.arguments:
                default_args += ', py::arg("{}")'.format(eachArg.name)
                if eachArg.default_value is not None:
                    default_args += ' = ' + eachArg.default_value

        method_dict = {'def_adorn': def_adorn,
                       'function_name': self.decl.name,
                       'function_docs': '" "',
                       'default_args': default_args}
        output_string += self.wrapper_templates["free_function"].format(**method_dict)
        return output_string
