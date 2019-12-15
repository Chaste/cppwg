import collections


class CppBaseWrapperWriter(object):

    """
    Base class for wrapper writers
    """

    def __init__(self, wrapper_templates):

        self.wrapper_templates = wrapper_templates
        self.tidy_replacements = collections.OrderedDict([(", ", "_"), ("<", "_lt_"), 
                                                          (">", "_gt_"), ("::", "_"), 
                                                          ("*", "Ptr"), ("&", "Ref"), 
                                                          ("-", "neg")])

    def tidy_name(self, name):
        
        """
        This method replaces full c++ declarations with a simple version for use
        in typedefs
        """

        for key, value in self.tidy_replacements.items():
            name = name.replace(key, value)
        return name.replace(" ", "")

    def exclusion_critera(self, decl, exclusion_args):
        
        """
        Fails if any of the types in the declaration appear in the exclusion args
        """        

        # Are any return types not wrappable
        return_type = decl.return_type.decl_string.replace(" ", "")
        if return_type in exclusion_args:
            return True

        # Are any arguments not wrappable
        for eachArg in decl.argument_types:
            arg_type = eachArg.decl_string.split()[0].replace(" ", "")
            if arg_type in exclusion_args:
                return True
        return False

    def default_arg_exclusion_criteria(self):

        return False
