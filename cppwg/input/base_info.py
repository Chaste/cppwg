from typing import Any, Optional


class BaseInfo:
    """
    Generic information structure for features (i.e packages, modules, cpp types, etc.)

    Attributes
    ----------
        name : str
            The feature name, as it appears in its definition.
        source_includes : list[str]
            A list of source files to be included with the feature.
        calldef_excludes : list[str]
            Do not include calldefs matching these patterns.
        smart_ptr_type : str, optional
            Handle classes with this smart pointer type.
        template_substitutions : dict[str, list[Any]]
            A list of template substitution sequences.
        pointer_call_policy : str, optional
            The default pointer call policy.
        reference_call_policy : str, optional
            The default reference call policy.
        extra_code : list[str]
            Any extra wrapper code for the feature.
        prefix_code : list[str]
            Any wrapper code that precedes the feature.
        custom_generator : str, optional
            A custom generator for the feature.
        excluded_methods : list[str]
            Do not include these methods.
        excluded_variables : list[str]
            Do not include these variables.
        constructor_arg_type_excludes : list[str]
            List of exlude patterns for ctors.
        return_type_excludes : list[str]
            List of exlude patterns for return types.
        arg_type_excludes : list[str]
            List of exlude patterns for arg types.
        name_replacements : dict[str, str]
            A list of name replacements.
    """

    def __init__(self, name):
        self.name: str = name
        self.source_includes: list[str] = []
        self.calldef_excludes: list[str] = []
        self.smart_ptr_type: Optional[str] = None
        self.template_substitutions: dict[str, list[Any]] = []
        self.pointer_call_policy: Optional[str] = None
        self.reference_call_policy: Optional[str] = None
        self.extra_code: list[str] = []
        self.prefix_code: list[str] = []
        self.custom_generator: Optional[str] = None
        self.excluded_methods: list[str] = []
        self.excluded_variables: list[str] = []
        self.constructor_arg_type_excludes: list[str] = []
        self.return_type_excludes: list[str] = []
        self.arg_type_excludes: list[str] = []
        self.name_replacements: dict[str, str] = {
            "double": "Double",
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
            "std::set": "Set",
        }

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
            if hasattr(self, "parent") and self.parent is not None:
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
            if hasattr(self, "parent") and self.parent is not None:
                att_list.extend(self.parent.hierarchy_attribute_gather(attribute_name))
        else:
            if hasattr(self, "parent") and self.parent is not None:
                att_list.extend(self.parent.hierarchy_attribute_gather(attribute_name))
        return att_list
