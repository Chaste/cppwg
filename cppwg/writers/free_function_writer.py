import base_writer


class CppFreeFunctionWrapperWriter(base_writer.CppBaseWrapperWriter):

    """
    Manage addition of free function wrapper code
    """

    def __init__(self, free_function_info, wrapper_templates):
        
        super(CppFreeFunctionWrapperWriter, self).__init__(wrapper_templates)

        self.free_function_info = free_function_info
        self.wrapper_templates = wrapper_templates
        self.exclusion_args = []

    def add_self(self, output_string):

        # Check for exclusions
        if self.exclusion_critera():
            return output_string

        # Which definition type
        def_adorn = ""

        # Get the arg signature
        arg_signature = ""
        arg_types = self.free_function_info.decl.argument_types
        num_arg_types = len(arg_types)
        for idx, eachArg in enumerate(arg_types):
            arg_signature += eachArg.decl_string
            if idx < num_arg_types-1:
                arg_signature += ", "

        # Default args
        default_args = ""
        if not self.default_arg_exclusion_criteria():
            for eachArg in self.free_function_info.decl:
                default_args += ', py::arg("{}")'.format(eachArg.name)
                if eachArg.default_value is not None:
                    default_args += ' = ' + eachArg.default_value

        method_dict = {'def_adorn': def_adorn,
                       'function_name': self.free_function_info.decl.name,
                       'function_docs': '" "',
                       'default_args': default_args}
        output_string += self.wrapper_templates["free_function"].format(**method_dict)
        return output_string
