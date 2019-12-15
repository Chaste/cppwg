from pygccxml import declarations

from cppwg.writers import base_writer

class CppMethodWrapperWriter(base_writer.CppBaseWrapperWriter):

    """
    Manage addition of method wrapper code
    """

    def __init__(self, class_info, 
                 method_decl,
                 class_decl,
                 wrapper_templates,
                 class_short_name=None):

        super(CppMethodWrapperWriter, self).__init__(wrapper_templates)

        self.class_info = class_info
        self.method_decl = method_decl
        self.class_decl = class_decl
        self.class_short_name = class_short_name
        if self.class_short_name is None:
            self.class_short_name = self.class_decl

    def exclusion_critera(self):

        # Are any return types not wrappable
        exclusion_args = self.class_info.hierarchy_attribute_gather('calldef_excludes')
        return_excludes = self.class_info.hierarchy_attribute_gather('return_type_excludes')
                
        return_type = self.method_decl.return_type.decl_string.replace(" ", "")
        if return_type in exclusion_args or return_type in return_excludes:
            return True

        # Don't include sub class (e.g. iterator) methods
        if self.method_decl.parent != self.class_decl:
            return True

        # No private methods without over-rides
        if self.method_decl.access_type == "private":
            return True

        # Are any arguments not wrappable
        tidied_excl = [x.replace(" ", "") for x in exclusion_args]
        for eachArg in self.method_decl.argument_types:
            arg_type = eachArg.decl_string.split()[0].replace(" ", "")
            if arg_type in tidied_excl:
                return True
            arg_type_full = eachArg.decl_string.replace(" ", "")
            if arg_type_full in tidied_excl:
                print (arg_type_full)
                return True            
        return False

    def add_self(self, output_string):

        # Check for exclusions
        if self.exclusion_critera():
            return output_string

        # Which definition type
        def_adorn = ""
        if self.method_decl.has_static:
            def_adorn += "_static"

        # How to point to class
        if not self.method_decl.has_static:
            self_ptr = self.class_short_name + "::*"
        else:
            self_ptr = "*"

        # Get the arg signature
        arg_signature = ""
        num_arg_types = len(self.method_decl.argument_types)
        for idx, eachArg in enumerate(self.method_decl.argument_types):
            arg_signature += eachArg.decl_string
            if idx < num_arg_types-1:
                arg_signature += ", "

        # Const-ness
        const_adorn = ""
        if self.method_decl.has_const:
            const_adorn = ' const '

        # Default args
        default_args = ""
        if not self.default_arg_exclusion_criteria():
            arg_types = self.method_decl.argument_types
            for idx, eachArg in enumerate(self.method_decl.arguments):
                default_args += ', py::arg("{}")'.format(eachArg.name)
                if eachArg.default_value is not None:
                    
                    # Hack for missing template in default args
                    repl_value = str(eachArg.default_value)
                    if "<DIM>" in repl_value:
                        if "<2>" in str(arg_types[idx]).replace(" ", ""):
                            repl_value = repl_value.replace("<DIM>","<2>")
                        elif "<3>" in str(arg_types[idx]).replace(" ", ""):
                            repl_value= repl_value.replace("<DIM>","<3>")
                    default_args += ' = ' + repl_value

        # Call policy
        pointer_call_policy = self.class_info.hierarchy_attribute('pointer_call_policy')
        reference_call_policy = self.class_info.hierarchy_attribute('reference_call_policy')
        
        call_policy = ""
        is_ptr = declarations.is_pointer(self.method_decl.return_type)
        if pointer_call_policy is not None and is_ptr:
            call_policy = ", py::return_value_policy::" + pointer_call_policy
        is_ref = declarations.is_reference(self.method_decl.return_type)
        if reference_call_policy is not None and is_ref:
            call_policy = ", py::return_value_policy::" + reference_call_policy
            
        method_dict = {'def_adorn': def_adorn,
                       'method_name': self.method_decl.name,
                       'return_type': self.method_decl.return_type.decl_string,
                       'self_ptr': self_ptr,
                       'arg_signature': arg_signature,
                       'const_adorn': const_adorn,
                       'class_short_name': self.class_short_name,
                       'method_docs': '" "',
                       'default_args': default_args,
                       'call_policy': call_policy}
        template = self.wrapper_templates["class_method"]
        output_string += template.format(**method_dict)
        return output_string

    def add_override(self, output_string):

        if self.method_decl.access_type == "private":
            return output_string

        arg_string = ""
        num_arg_types = len(self.method_decl.argument_types)
        args = self.method_decl.arguments
        for idx, eachArg in enumerate(self.method_decl.argument_types):
            arg_string += eachArg.decl_string + " " + args[idx].name
            if idx < num_arg_types-1:
                arg_string += ", "

        const_adorn = ""
        if self.method_decl.has_const:
            const_adorn = " const "

        overload_adorn = ""
        if self.method_decl.virtuality == "pure virtual":
                overload_adorn = "_PURE"

        all_args_string = ""
        for idx, eachArg in enumerate(self.method_decl.argument_types):
            all_args_string += ""*8 + args[idx].name
            if idx < num_arg_types-1:
                all_args_string += ", \n"

        return_string = self.method_decl.return_type.decl_string
        override_dict = {'return_type': return_string,
                         'method_name': self.method_decl.name,
                         'arg_string': arg_string,
                         'const_adorn': const_adorn,
                         'overload_adorn': overload_adorn,
                         'tidy_method_name': self.tidy_name(return_string),
                         'short_class_name': self.class_short_name,
                         'args_string': all_args_string,
                         }
        output_string += self.wrapper_templates["method_virtual_override"].format(**override_dict)
        return output_string
