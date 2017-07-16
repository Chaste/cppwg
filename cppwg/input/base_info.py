"""
Generic information structure for packages, modules and cpp types
"""


class BaseInfo(object):

    """
    :param: name - the feature name, as it appears in its definition
    :param: source_includes - a list of source files to be included with the feature
    :param: calldef_excludes - do not include calldefs matching these patterns
    :param: smart_ptr_type - handle classes with this smart pointer type
    :param: template_substitutions - a list of template substitution sequences
    :param: pointer_call_policy - the default pointer call policy
    :param: reference_call_policy - the default reference call policy
    :param: extra_code - any extra wrapper code for the feature
    :param: prefix_code - any wrapper code that precedes the feature
    :param: excluded_methods - do not include these methods
    :param: excluded_variables - do not include these variables
    :param: constructor_arg_type_excludes - list of exlude patterns for ctors
    :param: return_type_exludes - list of exlude patterns for return types
    :param: arg_type_excludes - list of exlude patterns for arg types 
    """

    def __init__(self, name):
        
        self.name = name
        self.source_includes = []
        self.calldef_excludes = []
        self.smart_ptr_type = None
        self.template_substitutions = []  
        self.pointer_call_policy = None
        self.reference_call_policy = None
        self.extra_code = []
        self.prefix_code = []
        self.custom_generator = None
        self.excluded_methods = None
        self.excluded_variables = None
        self.constructor_arg_type_excludes = []
        self.return_type_excludes = []
        self.arg_type_excludes = []
        self.name_replacements = {"double": "Double",
                                  "unsigned int": "Unsigned",
                                  "Unsigned int": "Unsigned",
                                  "unsigned": "Unsigned",
                                  "double": "Double",
                                  "std::vector": "Vector",
                                  "std::pair": "Pair",
                                  "std::map": "Map",
                                  "std::string": "String",
                                  "boost::shared_ptr": "SharedPtr",
                                  "*": "Ptr",
                                  "c_vector": "CVector",
                                  "std::set": "Set"}
        
    @property
    def parent(self):
        return None
    
    def hierarchy_attribute(self, attribute_name):
        
        """
        For the supplied attribute iterate through parents until a non None
        value is found. If the tope level parent attribute is None, return None.
        """
        
        if hasattr(self, attribute_name) and getattr(self, attribute_name) is not None:
            return getattr(self, attribute_name)
        else:
            if hasattr(self, 'parent') and self.parent is not None: 
                return self.parent.hierarchy_attribute(attribute_name)   
            else:
                return None

    def hierarchy_attribute_gather(self, attribute_name):
        
        """
        For the supplied attribute iterate through parents gathering list entries.
        """
        
        att_list = []
        if hasattr(self, attribute_name) and getattr(self, attribute_name) is not None:
            att_list.extend(getattr(self, attribute_name))
            if hasattr(self, 'parent') and self.parent is not None: 
                att_list.extend(self.parent.hierarchy_attribute_gather(attribute_name)) 
        else:
            if hasattr(self, 'parent') and self.parent is not None: 
                att_list.extend(self.parent.hierarchy_attribute_gather(attribute_name))             
        return att_list               