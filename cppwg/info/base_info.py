"""Generic information structure."""

import copy
import importlib.util
import logging
import os
import sys
from abc import ABC, abstractmethod
from numbers import Number
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cppwg.templates.custom import Custom


# The configuration options shared by every info level (package, module, class,
# free function, ...), each mapped to its default value. This is the single
# source of truth for the shared options: BaseInfo seeds these as attribute
# defaults and copies any the config overrides, and the parser
# (cppwg.parsers.package_info_parser) builds its config dicts from the same
# schema. An option added here is therefore understood everywhere - defined in
# one place instead of being restated in BaseInfo and the parser (which is how
# options such as name_replacements previously became unreachable from the YAML).
# Mutable defaults are deep-copied per use so no two objects share a list/dict.
# See the class Attributes docstring for what each option means; tri-state
# options default to None, meaning "inherit from further up the info tree".
BASE_INFO_OPTIONS: dict[str, Any] = {
    "arg_type_excludes": [],
    "auto_includes": None,
    "calldef_excludes": [],
    "constructor_arg_type_excludes": [],
    "constructor_signature_excludes": [],
    "custom_generator": "",
    "discover_arg_excludes": {},
    "discover_template_instantiations": None,
    "excluded": False,
    "excluded_methods": [],
    "excluded_variables": [],
    "export_values": None,
    "name_replacements": {
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
    },
    "pointer_call_policy": "",
    "prefix_code": [],
    "prefix_text": "",
    "reference_call_policy": "",
    "return_type_excludes": [],
    "smart_ptr_type": "",
    "source_includes": [],
    "source_root": "",
    "suffix_code": [],
    "template_substitutions": [],
}

# Options copied from the config but deliberately not in BASE_INFO_OPTIONS:
# exclude_inherited_overrides is a tri-state the parser seeds per level (package
# False, module/class None) to drive the package->module->class cascade, so it
# must not be given a single shared default here.
_EXTRA_CONFIG_KEYS: tuple[str, ...] = ("exclude_inherited_overrides",)


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
        Exclude any method, constructor or free function with an argument of one
        of these types. Patterns match a type as a whole token (so `Shape` does
        not match `AbstractShape`).
    auto_includes : bool | None
        Automatically add `#include`s for the project types a class's wrapped
        method/constructor signatures use, when the class's own header only
        forward-declares them (so the wrapper still compiles without listing them
        by hand under `source_includes`). Only project types - classes defined
        under the module `source_locations` - are resolved; library types are
        left alone. None (the default) means inherit from further up the info
        tree, where it is treated as off (opt-in); set it to True or False at any
        level (package, module or class). Has no effect with
        `common_include_file` (the common header already includes everything).
    calldef_excludes : list[str]
        Deprecated: use arg_type_excludes and/or return_type_excludes. Kept for
        backwards compatibility; treated as both arg_type_excludes and
        return_type_excludes.
    constructor_arg_type_excludes : list[str]
        Exclude constructors (only) with an argument of one of these types, for
        the case where a type should be excluded from constructors but not
        methods. Matched the same way as arg_type_excludes.
    constructor_signature_excludes : list[list[str]]
        List of exclude patterns for constructor signatures.
    custom_generator : str
        A custom generator for the feature.
    discover_arg_excludes : dict[str, list]
        Drop a *discovered* template instantiation when the argument bound to a
        named template parameter is one of the listed values, e.g.
        `{SPACE_DIM: [1]}` drops `Foo<SPACE_DIM=1>` but keeps `Foo<SPACE_DIM=2>`.
        Matching is by parameter name, so a value that is spatial for one
        parameter but incidental for another - e.g. a trailing `PROBLEM_DIM` of 1
        in `Bar<2, 2, 1>` - is only excluded where it is actually named. Only
        instantiations found by discovery are filtered; `template_substitutions`
        are wrapped as written. Set at any level (package, module or class); it
        inherits down the info tree.
    discover_template_instantiations : bool | None
        Discover template instantiations for templated classes automatically by
        scanning the C++ source files (see PackageInfo.source_cpp_patterns) for
        explicit instantiations e.g. `template class Foo<2>;`. Used as a fallback
        to populate template arguments when no `template_substitutions` matched.
        None (the default) means inherit from further up the info tree; set it to
        True or False at any level (package, module or class).
    excluded: bool
        Exclude this feature.
    excluded_methods : list[str]
        Do not include these methods.
    excluded_variables : list[str]
        Do not include these variables.
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
        Exclude any method or free function returning one of these types.
        Matched the same way as arg_type_excludes.
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

    custom_generator_instance : cppwg.templates.custom.Custom | None
        An instance of the custom generator class, or None if not set.
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

        # Seed the shared options from the single schema, deep-copying each
        # default so no two info objects share a mutable list/dict. See the
        # Attributes docstring for what each option means.
        for key, default in BASE_INFO_OPTIONS.items():
            setattr(self, key, copy.deepcopy(default))

        self.custom_generator_instance: "Custom | None" = None

        if info_config:
            # Copy any option the config provides, over the schema defaults.
            # Deep-copy each value: the parser shallow-copies one base_config into
            # every package/module/class config, so the same list/dict object
            # reaches many info objects; without this copy they would alias it (a
            # later mutation of one object's option would leak to its siblings and
            # parent). exclude_inherited_overrides (in _EXTRA_CONFIG_KEYS) is
            # copied when present but has no shared default - the parser seeds it
            # per level.
            for key in (*BASE_INFO_OPTIONS, *_EXTRA_CONFIG_KEYS):
                if key in info_config:
                    setattr(self, key, copy.deepcopy(info_config[key]))

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

    def hierarchy_attribute_gather_flat(self, attribute_name: str) -> list[Any]:
        """
        Gather a list-valued attribute across the info tree, flattened one level.

        hierarchy_attribute_gather returns one entry per hierarchy level that
        defines the attribute; for a list-valued option each entry is itself a
        list. This flattens those into a single list of the option's items
        across all levels (e.g. all exclude patterns from class, module and
        package).

        Only actual sequences (list/tuple/set) are flattened; any other value
        (e.g. a yaml `option: foo` written instead of the expected
        `option: [foo]`) is treated as a single item rather than being iterated
        - which for a str would split it into individual characters.

        Parameters
        ----------
        attribute_name : str
            The attribute name to search for.

        Returns
        -------
        list[Any]
            The flattened list of items.
        """
        flat: list[Any] = []
        for value in self.hierarchy_attribute_gather(attribute_name):
            if isinstance(value, (list, tuple, set)):
                flat.extend(value)
            else:
                flat.append(value)
        return flat
