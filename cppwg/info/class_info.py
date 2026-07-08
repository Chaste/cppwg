"""Class information structure."""

import logging
import os
from typing import TYPE_CHECKING, Any

from pygccxml.declarations.matchers import access_type_matcher_t
from pygccxml.declarations.runtime_errors import declaration_not_found_t

from cppwg.info.cpp_entity_info import CppEntityInfo
from cppwg.utils import utils

if TYPE_CHECKING:
    from pygccxml.declarations import declaration_t
    from pygccxml.declarations.namespace import namespace_t


def _unqualified_base_name(name: str) -> str:
    """
    Reduce a class name to its unqualified base name for matching.

    Strips any namespace qualification and template arguments, e.g.
    ``"foo::Bar<1, 1>"`` -> ``"Bar"``. Used to match a base class declaration
    to the wrapped class that provides it without relying on declaration
    identity, which pygccxml does not preserve across template/typedef
    resolution.
    """
    return name.split("<", 1)[0].rsplit("::", 1)[-1].strip()


class CppClassInfo(CppEntityInfo):
    """
    An information structure for individual C++ classes to be wrapped.

    Attributes
    ----------
    base_decls : pygccxml.declarations.declaration_t
        Declarations for the base classes, one per template instantiation
    cpp_names : list[str]
        The C++ names of the class e.g. ["Foo<2,2>", "Foo<3,3>"]
    py_names : list[str]
        The Python names of the class e.g. ["Foo_2_2", "Foo_3_3"]
    """

    def __init__(self, name: str, class_config: dict[str, Any] | None = None):
        super().__init__(name, class_config)

        self.base_decls: list["declaration_t"] = []
        self.cpp_names: list[str] = []
        self.py_names: list[str] = []

        # Cache for template parameter names read from the source header, so the
        # header is not read twice during discovery (once to decide whether the
        # class is templated, once to record its parameter names).
        self._source_template_params: list[str] | None = None

        # Whether template_arg_lists came from instantiation discovery (as opposed
        # to template_substitutions). The CastXML fallback only merges into
        # discovery-derived args; template_substitutions take precedence.
        self.template_args_from_discovery: bool = False

    def extract_templates_from_source(self) -> None:
        """
        Extract template args from the associated source file.

        Search the source file for a class signature matching one of the
        template signatures defined in `template_substitutions`. If a match
        is found, set the corresponding template arg replacements for the class.
        """
        # Skip if there are template args attached directly to the class
        if self.template_arg_lists:
            return

        # Skip if there is no source file
        source_path = self.source_file_path
        if not source_path:
            return

        # Get list of template substitutions applicable to this class
        # e.g. [ {"signature":"<int A, int B>", "replacement":[[2,2], [3,3]]} ]
        substitutions = self.hierarchy_attribute_gather_flat("template_substitutions")

        # Skip if there are no applicable template substitutions
        if not substitutions:
            return

        source = utils.read_source_file(
            source_path,
            strip_comments=True,
            strip_preprocessor=True,
            strip_whitespace=True,
        )

        # Search for template signatures in the source file
        for substitution in substitutions:
            # Skip a mis-typed entry: each substitution must be a dict with a
            # signature and a replacement (a yaml scalar or malformed entry
            # would otherwise raise here).
            if (
                not isinstance(substitution, dict)
                or "signature" not in substitution
                or "replacement" not in substitution
            ):
                continue

            # Signature e.g. <int A, int B>
            signature = substitution["signature"].strip()

            class_list = utils.find_classes_in_source(
                source,
                class_name=self.name,
                template_signature=signature,
            )

            if class_list:
                self.template_signature = signature

                # Replacement e.g. [[2,2], [3,3]]
                self.template_arg_lists = substitution["replacement"]

                # Extract parameters ["A", "B"] from "<int A, int B = A>"
                self.template_params = utils.parse_template_params(signature)
                break

    def template_params_from_source(self) -> list[str]:
        """
        Return the class's template parameter names from its header source.

        Reads the class's source file and extracts the parameter names from its
        template declaration e.g. ["ELEMENT_DIM", "SPACE_DIM"] from
        `template <unsigned ELEMENT_DIM, unsigned SPACE_DIM> class Foo`.

        Returns
        -------
        list[str]
            The template parameter names, or an empty list if the class has no
            source file or is not templated.
        """
        if self._source_template_params is not None:
            return self._source_template_params

        if not self.source_file_path:
            return []

        source = utils.read_source_file(
            self.source_file_path,
            strip_comments=True,
            strip_preprocessor=True,
            strip_whitespace=True,
        )
        self._source_template_params = utils.find_template_params_in_source(
            source, self.name
        )
        return self._source_template_params

    def template_has_defaulted_params(self) -> bool:
        """
        Check whether the class's header template declaration has a default.

        e.g. True for `template <unsigned A, unsigned B = A> class Foo`. Used to
        decide whether a CastXML version that drops defaulted trailing arguments
        can be trusted for this class when merging fallback instantiations.

        Returns
        -------
        bool
            True if the class is templated with at least one defaulted parameter.
        """
        if not self.source_file_path:
            return False

        source = utils.read_source_file(
            self.source_file_path,
            strip_comments=True,
            strip_preprocessor=True,
            strip_whitespace=True,
        )
        return utils.template_has_default_param(source, self.name)

    def apply_template_instantiations(
        self,
        instantiation_map: dict[str, list[list[str]]],
        merge: bool = False,
        trust_defaulted_args: bool = True,
    ) -> None:
        """
        Populate template args from explicit instantiations found in source.

        If template instantiation discovery is enabled for this class and the map
        holds arg lists for its name, adopt them and rebuild the class names.
        `template_substitutions` (which sets template_arg_lists in
        extract_templates_from_source) takes precedence and is never extended.

        Parameters
        ----------
        instantiation_map : dict[str, list[list[str]]]
            Map of base class name to discovered template arg lists,
            e.g. {"Foo": [["2"], ["3"]]}.
        merge : bool
            If True, merge the arg lists into args already discovered for this
            class (used for the CastXML fallback, so macro instantiations add to
            text-scanned ones) rather than only setting args when it has none.
        trust_defaulted_args : bool
            Whether these arg lists render defaulted trailing template arguments
            reliably (CastXML >= 0.6.0). When False, a merge into a class with
            defaulted template parameters is skipped (with a warning) to avoid
            adding a differently-rendered duplicate of an existing instantiation.
        """
        logger = logging.getLogger()

        if self.excluded:
            return

        # Skip unless discovery is enabled somewhere up the info tree
        if not self.hierarchy_attribute("discover_template_instantiations"):
            return

        arg_lists = instantiation_map.get(self.name)
        if not arg_lists:
            return

        if self.template_arg_lists:
            # Args already set. Only merge into discovery-derived args; args from
            # template_substitutions take precedence and are left untouched.
            if not merge or not self.template_args_from_discovery:
                return

            # Guard the CastXML defaulted-arg rendering hazard: if this source
            # drops defaulted trailing args, merging its lists into text-scanned
            # ones could add a differently-rendered duplicate (e.g. "Foo<2>" for
            # an existing "Foo<2, 2>"). Skip the merge; warn only when the
            # fallback plausibly holds additional instantiations (more arg lists
            # than are already known), to avoid noise for classes whose fallback
            # args are just the text-scanned ones re-rendered.
            if not trust_defaulted_args and self.template_has_defaulted_params():
                if len(arg_lists) > len(self.template_arg_lists):
                    logger.warning(
                        f"Not merging fallback-discovered instantiations for "
                        f"{self.name}: it has defaulted template parameters and "
                        "the CastXML version does not preserve them (upgrade to "
                        "CastXML >= 0.6.0)."
                    )
                return

            new_args = [a for a in arg_lists if a not in self.template_arg_lists]
            if not new_args:
                return
            self.template_arg_lists = self.template_arg_lists + new_args
        else:
            self.template_arg_lists = arg_lists

        self.template_args_from_discovery = True

        # Recover the template parameter names from the class's header template
        # declaration (the instantiated decls do not carry them). These are used
        # to substitute template params appearing in method/constructor default
        # argument values e.g. `= SPACE_DIM` -> `= 2`.
        self.template_params = self.template_params_from_source()

        # Rebuild the C++/Python names now that template args are known
        # (update_names was already called for the untemplated case).
        self.cpp_names = []
        self.py_names = []
        self.update_names()

    def extends(self, other: "CppClassInfo") -> bool:
        """
        Check if the class extends the specified class.

        Base classes are matched by name (unqualified, template arguments
        stripped) rather than by declaration identity: pygccxml may represent a
        base as a different declaration object than the one held by the wrapped
        class - e.g. after resolving a templated class via its typedef, or when
        the base instantiation is added later by base-class discovery - so an
        identity/equality match is unreliable.

        Parameters
        ----------
        other : CppClassInfo
            The other class to check

        Returns
        -------
        bool
            True if the class extends the specified class, False otherwise
        """
        if not self.base_decls:
            return False
        target = _unqualified_base_name(other.name)
        return any(
            base_decl is not None
            and _unqualified_base_name(base_decl.name) == target
            for base_decl in self.base_decls
        )

    def signature_arg_types(self) -> list[str]:
        """
        Return the decl strings of all public method and constructor argument
        types across this class's instantiations.

        Returns
        -------
        list[str]
            The argument type decl strings, e.g. ``["Foo<2> const &", "double"]``.
        """
        query = access_type_matcher_t("public")
        arg_types: list[str] = []
        for class_decl in self.decls:
            for method_decl in class_decl.member_functions(
                function=query, allow_empty=True
            ):
                arg_types.extend(
                    arg_type.decl_string for arg_type in method_decl.argument_types
                )
            for ctor_decl in class_decl.constructors(function=query, allow_empty=True):
                arg_types.extend(
                    arg_type.decl_string for arg_type in ctor_decl.argument_types
                )
        return arg_types

    def requires(self, other: "CppClassInfo") -> bool:
        """
        Check if the specified class is used in method signatures of this class.

        Parameters
        ----------
        other : CppClassInfo
            The specified class to check.

        Returns
        -------
        bool
            True if the specified class is used in method signatures of this class.
        """
        return any(
            utils.type_string_matches(arg_type, other.name)
            for arg_type in self.signature_arg_types()
        )

    def update_from_ns(self, source_ns: "namespace_t") -> None:
        """
        Update class with information from the source namespace.

        Adds the class declarations and base class declarations.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        logger = logging.getLogger()

        # Skip excluded classes
        if self.excluded:
            return

        # template_arg_lists is parallel to cpp_names/py_names for a templated
        # class, and the writers index it by position, so keep the three in
        # lockstep as unresolved instantiations are dropped below.
        has_template_args = bool(self.template_arg_lists)
        keep_cpp: list[str] = []
        keep_py: list[str] = []
        keep_args: list[list[Any]] = []
        for index, (class_cpp_name, class_py_name) in enumerate(
            zip(self.cpp_names, self.py_names)
        ):
            try:
                cpp_name = class_cpp_name.replace(" ", "")  # e.g. Foo<2,2,1>
                class_decl = source_ns.class_(cpp_name)

            except declaration_not_found_t:
                # Parsed names for templated classes which have default args
                # may vary between CastXML versions and compiler versions.
                # Try to look up the class name via the typedef e.g. for
                # `template <int A, int B=A, int C=1> class Foo {};`
                # the parsed name for Foo<2,2,1> could be Foo<2,2>, or Foo<2>
                # but the typedef name will always be Foo_2_2_1
                py_name = class_py_name.replace(" ", "")  # e.g. Foo_2_2_1
                try:
                    typedef_decl = source_ns.typedef(py_name)
                    class_decl = typedef_decl.decl_type.declaration
                except declaration_not_found_t:
                    # No declaration for this name. This happens for a templated
                    # class that opted into discovery but has no explicit
                    # instantiation to discover (e.g. an abstract base only ever
                    # used as a base or through pointers). Skip it rather than
                    # aborting - it may still be resolved from the base-class
                    # hierarchy of a wrapped class (see
                    # PackageInfo.discover_base_class_instantiations), otherwise
                    # add template_substitutions to wrap it explicitly.
                    logger.info(
                        f"No declaration found for {class_cpp_name} yet; "
                        "deferring."
                    )
                    continue

                logger.info(f"Found {class_decl.name} for {class_cpp_name}")
                class_decl.name = class_cpp_name

            self.decls.append(class_decl)
            keep_cpp.append(class_cpp_name)
            keep_py.append(class_py_name)
            if has_template_args:
                keep_args.append(self.template_arg_lists[index])

        self.cpp_names = keep_cpp
        self.py_names = keep_py
        if has_template_args:
            self.template_arg_lists = keep_args

        # Update the class source file if not already set
        if not self.source_file_path and self.decls:
            self.source_file_path = self.decls[0].location.file_name
            self.source_file = os.path.basename(self.source_file_path)

        # Update the base class declarations
        self.base_decls = [
            base.related_class for decl in self.decls for base in decl.bases
        ]

    def update_from_source(self, source_file_paths: list[str]) -> None:
        """
        Update class with information from the source headers.

        Parameters
        ----------
        source_file_paths : list[str]
            A list of source file paths
        """
        # Skip excluded classes
        if self.excluded:
            return

        # Attempt to map class to a source file
        if self.source_file_path:
            self.source_file = os.path.basename(self.source_file_path)
        else:
            for file_path in source_file_paths:
                file_name = os.path.basename(file_path)
                # Match file name if set
                if self.source_file == file_name:
                    self.source_file_path = file_path
                # Match class name, assuming the file name is the class name
                elif self.name == os.path.splitext(file_name)[0]:
                    self.source_file = file_name
                    self.source_file_path = file_path

        # Extract template args from the source file
        self.extract_templates_from_source()

        # Update the C++ and Python class names
        self.update_names()

    def update_py_names(self) -> None:
        """
        Set the Python names for the class, accounting for template args.

        Set the name(s) of the class as it should appear in Python. This
        collapses template arguments, separates them by underscores, and removes
        special characters. There can be multiple names, one for each template
        class instantiation. For example, class "Foo" with template arguments
        [[2, 2], [3, 3]] will have a Python name list ["Foo_2_2", "Foo_3_3"].
        """
        # Handles untemplated classes
        if not self.template_arg_lists:
            if self.name_override:
                self.py_names.append(self.name_override)
            else:
                self.py_names.append(self.name)
            return

        # Table of special characters for removal
        rm_chars = {"<": None, ">": None, ",": None, " ": None}
        rm_table = str.maketrans(rm_chars)

        # Clean the class name
        class_name = self.name
        if self.name_override:
            class_name = self.name_override

        # Do standard name replacements e.g. "unsigned int" -> "Unsigned"
        for name, replacement in self.name_replacements.items():
            class_name = class_name.replace(name, replacement)

        # Remove special characters
        class_name = class_name.translate(rm_table)

        # Capitalize the first letter e.g. "foo" -> "Foo"
        if len(class_name) > 1:
            class_name = class_name[0].capitalize() + class_name[1:]

        # Create a string of template args separated by "_" e.g. 2_2
        for template_arg_list in self.template_arg_lists:
            # Example template_arg_list : [2, 2]

            template_string = ""
            for idx, arg in enumerate(template_arg_list):
                # Do standard name replacements
                arg_str = str(arg)
                for name, replacement in self.name_replacements.items():
                    arg_str = arg_str.replace(name, replacement)

                # Remove special characters
                arg_str = (
                    arg_str.replace("<", "_").replace(",", "_").translate(rm_table)
                )

                # Capitalize the first letter
                if len(arg_str) > 1:
                    arg_str = arg_str[0].capitalize() + arg_str[1:]

                # Add "_" between template arguments
                template_string += arg_str
                if idx < len(template_arg_list) - 1:
                    template_string += "_"

            self.py_names.append(class_name + "_" + template_string)

    def update_cpp_names(self) -> None:
        """
        Set the C++ names for the class, accounting for template args.

        Set the name(s) of the class as it appears in C++. There can be
        multiple names, one for each template class instantiation.
        For example, a class "Foo" with template arguments [[2, 2], [3, 3]]
        will have a C++ name list ["Foo<2, 2>", "Foo<3, 3>"].
        """
        # Handles untemplated classes
        if not self.template_arg_lists:
            self.cpp_names.append(self.name)
            return

        for template_arg_list in self.template_arg_lists:
            # Create template string from arg list e.g. [2, 2] -> "<2, 2>"
            template_string = ", ".join([str(arg) for arg in template_arg_list])
            template_string = "<" + template_string + ">"

            # Join full name e.g. "Foo<2, 2>"
            self.cpp_names.append(self.name + template_string)

    def update_names(self) -> None:
        """
        Update the C++ and Python names for the class.
        """
        self.update_cpp_names()
        self.update_py_names()
