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
                for part in signature.split(","):
                    param = (
                        part.strip()
                        .replace("<", "")
                        .replace(">", "")
                        .split(" ")[1]
                        .split("=")[0]
                        .strip()
                    )
                    self.template_params.append(param)
                break

    def extends(self, other: "CppClassInfo") -> bool:
        """
        Check if the class extends the specified class.

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
        if not other.decls:
            return False
        return any(decl in other.decls for decl in self.base_decls)

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
        if not self.decls:
            return False

        query = access_type_matcher_t("public")

        for class_decl in self.decls:
            method_decls = class_decl.member_functions(function=query, allow_empty=True)
            for method_decl in method_decls:
                for arg_type in method_decl.argument_types:
                    if utils.type_string_matches(arg_type.decl_string, other.name):
                        return True

            ctor_decls = class_decl.constructors(function=query, allow_empty=True)
            for ctor_decl in ctor_decls:
                for arg_type in ctor_decl.argument_types:
                    if utils.type_string_matches(arg_type.decl_string, other.name):
                        return True
        return False

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

        for class_cpp_name, class_py_name in zip(self.cpp_names, self.py_names):
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
                typedef_decl = source_ns.typedef(py_name)
                class_decl = typedef_decl.decl_type.declaration

                logger.info(f"Found {class_decl.name} for {class_cpp_name}")
                class_decl.name = class_cpp_name

            self.decls.append(class_decl)

        # Update the class source file if not already set
        if not self.source_file_path:
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
