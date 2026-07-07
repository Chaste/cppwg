"""Generic information structure."""

import importlib.util
import logging
import os
import sys
from abc import ABC, abstractmethod
from numbers import Number
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cppwg.templates.custom import Custom


class BaseInfo(ABC):
    """
    A generic information structure for features.

    Features include packages, modules, classes, free functions, etc.
    Information structures are used to store information about the features.
    BaseInfo is the base information structure, and set up attributes that are
    common to all features.

    Attributes
    ----------
    arg_type_excludes : list[str]
        List of exclude patterns for arg types in methods.
    calldef_excludes : list[str]
        Do not include calldefs matching these patterns.
    constructor_arg_type_excludes : list[str]
        List of exclude patterns for arg types in constructors.
    constructor_signature_excludes : list[list[str]]
        List of exclude patterns for constructor signatures.
    custom_generator : str
        A custom generator for the feature.
    excluded: bool
        Exclude this feature.
    excluded_methods : list[str]
        Do not include these methods.
    excluded_variables : list[str]
        Do not include these variables.
    extra_code : list[str]
        Any extra wrapper code for the feature.
    name : str
        The name of the package, module, class etc. represented by this object.
    name_replacements : dict[str, str]
        A dictionary of name replacements e.g. {"double":"Double"}
    pointer_call_policy : str
        The default pointer call policy.
    prefix_code : list[str]
        Custom wrapper code that comes before the auto-generated feature code.
    prefix_text : str
        Text to add at the top of all wrappers.
    reference_call_policy : str
        The default reference call policy.
    return_type_excludes : list[str]
        List of exclude patterns for return types.
    smart_ptr_type : str
        Handle classes with this smart pointer type.
    source_includes : list[str]
        A list of source files to be included with the feature.
    source_root : str
        The root directory of the C++ source code.
    suffix_code : list[str]
        Custom wrapper code that comes after the auto-generated feature code.
    template_substitutions : list[dict[str, Any]]
        A list of template substitution sequences.

    custom_generator_instance : cppwg.templates.custom.Custom
        An instance of the custom generator class.
    """

    def __init__(self, name: str, info_config: dict[str, Any] | None = None) -> None:
        """
        Create a base info object from a config dict.

        Parameters
        ----------
        name : str
            The name of the package, module, class, etc. represented by this object.
        info_config : dict[str, Any]
            A dictionary of configuration settings
        """
        self.name: str = name

        # Paths
        self.source_includes: list[str] = []
        self.source_root: str = ""

        # Exclusions
        self.arg_type_excludes: list[str] = []
        self.calldef_excludes: list[str] = []
        self.constructor_arg_type_excludes: list[str] = []
        self.constructor_signature_excludes: list[list[str]] = []
        self.excluded: bool = False
        self.excluded_methods: list[str] = []
        self.excluded_variables: list[str] = []
        self.return_type_excludes: list[str] = []

        # Pointers
        self.pointer_call_policy: str = ""
        self.reference_call_policy: str = ""
        self.smart_ptr_type: str = ""

        # Substitutions
        self.template_substitutions: list[dict[str, Any]] = []
        self.name_replacements: dict[str, str] = {
            "double": "Double",
            "unsigned int": "Unsigned",
            "Unsigned int": "Unsigned",
            "unsigned": "Unsigned",
            "std::vector": "Vector",
            "std::pair": "Pair",
            "std::map": "Map",
            "std::string": "String",
            "boost::shared_ptr": "SharedPtr",
            "*": "Ptr",
            "c_vector": "CVector",
            "std::set": "Set",
        }

        # Custom Code
        self.extra_code: list[str] = []
        self.prefix_code: list[str] = []
        self.prefix_text: str = ""
        self.custom_generator: str = ""

        self.custom_generator_instance: "Custom" = None

        if info_config:
            for key in [
                "arg_type_excludes",
                "calldef_excludes",
                "constructor_arg_type_excludes",
                "constructor_signature_excludes",
                "custom_generator",
                "excluded",
                "excluded_methods",
                "excluded_variables",
                "extra_code",
                "name_replacements",
                "pointer_call_policy",
                "prefix_code",
                "prefix_text",
                "reference_call_policy",
                "return_type_excludes",
                "smart_ptr_type",
                "source_includes",
                "source_root",
                "suffix_code",
                "template_substitutions",
            ]:
                if key in info_config:
                    setattr(self, key, info_config[key])

        self.load_custom_generator()

    @property
    @abstractmethod
    def parent(self) -> "BaseInfo | None":
        """
        Returns this object's parent node in the info tree hierarchy.

        This property is supplied by subclasses e.g. a ModuleInfo's parent
        is a PackageInfo, a CppClassInfo's parent is a ModuleInfo etc.

        Returns
        -------
        BaseInfo | None
            The parent node in the info tree hierarchy.
        """

    def load_custom_generator(self) -> None:
        """
        Check if a custom generator is specified and load it.
        """
        if not self.custom_generator:
            return

        logger = logging.getLogger()
        logger.info(f"Custom generator for {self.name}: {self.custom_generator}")

        # Load the custom generator as a module
        location = os.path.splitext(self.custom_generator)[0]  # /path/to/FooGen
        class_name = os.path.basename(location)  # FooGen

        spec = importlib.util.spec_from_file_location(location, self.custom_generator)
        module = importlib.util.module_from_spec(spec)
        sys.modules[location] = module  # location is the module name
        spec.loader.exec_module(module)

        # Get the custom generator class from the loaded module.
        # Note: The custom generator class name must match the filename.
        CustomGeneratorClass = getattr(module, class_name)

        # Instantiate the custom generator from the provided class
        self.custom_generator_instance = CustomGeneratorClass()

    def hierarchy_attribute(self, attribute_name: str) -> Any:
        """
        Get the attribute value from this object or one further up the info tree.

        Ascend the info tree hierarchy searching for the attribute and return
        the first value found for it.

        Parameters
        ----------
        attribute_name : str
            The attribute name to search for.

        Returns
        -------
        Any
            The attribute value, or None if not found.
        """
        value = getattr(self, attribute_name, None)
        if value or isinstance(value, bool) or isinstance(value, Number):
            return value

        if self.parent is None:
            # Reached the top of the hierarchy (i.e. PackageInfo)
            return None

        return self.parent.hierarchy_attribute(attribute_name)

    def hierarchy_attribute_gather(self, attribute_name: str) -> list[Any]:
        """
        Get a list of attribute values from this object and others in the info tree.

        Ascend the info tree hierarchy searching for the attribute and return
        a list of all the values found for it.

        Parameters
        ----------
        attribute_name : str
            The attribute name to search for.

        Returns
        -------
        list[Any]
            The list of attribute values.
        """
        value_list: list[Any] = []

        value = getattr(self, attribute_name, None)
        if value or isinstance(value, bool) or isinstance(value, Number):
            value_list.append(value)

        if self.parent is None:
            # Reached the top of the hierarchy (i.e. PackageInfo)
            return value_list

        value_list.extend(self.parent.hierarchy_attribute_gather(attribute_name))
        return value_list
