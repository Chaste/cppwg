"""Package information structure."""

import fnmatch
import logging
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pygccxml import declarations
from pygccxml.declarations.matchers import access_type_matcher_t

from cppwg.info.base_info import BaseInfo
from cppwg.utils import utils
from cppwg.utils.constants import CPPWG_EXT

# Matches a template-id such as "Foo<2, 2>". [^<>] confines each match to a
# single, innermost argument list, so "boost::shared_ptr<PottsMesh<2>>" yields
# the inner "PottsMesh<2>" (the type whose instantiation actually matters), not
# the library shared_ptr wrapping it.
_TEMPLATE_ID_RE = re.compile(r"[A-Za-z_][\w:]*<[^<>]*>")


def _referenced_instantiations(decl_string: str) -> "Iterator[tuple[str, str]]":
    """
    Yield (unqualified base, normalised full name) for template-ids in a type.

    e.g. "::Facet<0> *" -> ("Facet", "Facet<0>"); "std::vector<double>" ->
    ("vector", "std::vector<double>").

    Parameters
    ----------
    decl_string : str
        A pygccxml type declaration string.

    Yields
    ------
    tuple[str, str]
        The unqualified base class name and the whitespace-stripped full name.
    """
    for match in _TEMPLATE_ID_RE.finditer(decl_string):
        full = match.group(0).replace(" ", "").lstrip(":")
        base = full.split("<", 1)[0].split("::")[-1]
        yield base, full


if TYPE_CHECKING:
    from pygccxml.declarations.namespace import namespace_t

    from cppwg.info.module_info import ModuleInfo


class PackageInfo(BaseInfo):
    """
    A structure to hold information about the package.

    Attributes
    ----------
    common_include_file : bool
        Use a common include file for all source files
    exceptions : list[str | dict[str, str]]
        C++ exception classes to translate into Python exceptions. Each entry is
        a class name, or a dict with a `name` and an optional `message_method`
        (the accessor for the message, defaulting to "what"). A pybind11
        exception translator is generated automatically for each.
    exclude_default_args : bool
        Exclude default arguments from method wrappers.
    name : str
        The name of the package
    source_cpp_patterns : list[str]
        A list of implementation file patterns to scan for explicit template
        instantiations when `discover_template_instantiations` is enabled.
    source_hpp_patterns : list[str]
        A list of source file patterns to include

    exception_info : list[dict[str, str]]
        Resolved exception translation data (cpp_type, message_expr,
        source_file), populated from `exceptions` after parsing the source.
    module_collection : list[ModuleInfo]
        A list of module info objects associated with this package
    source_cpp_files : list[str]
        A list of implementation file paths collected for template instantiation
        discovery. These are not added to the header collection.
    source_hpp_files : list[str]
        A list of source file names to include
    """

    def __init__(
        self, name: str, package_config: dict[str, Any] | None = None
    ) -> None:
        """
        Create a package info object from a package_config dict.

        Parameters
        ----------
        name : str
            The name of the package
        package_config : dict[str, Any]
            A dictionary of package configuration settings
        """
        super().__init__(name, package_config)

        self.common_include_file: bool = False
        self.exceptions: list[str | dict[str, str]] = []
        self.exclude_default_args: bool = False
        self.source_cpp_patterns: list[str] = ["*.cpp"]
        self.source_hpp_patterns: list[str] = ["*.hpp"]

        self.exception_info: list[dict[str, str]] = []
        self.module_collection: list["ModuleInfo"] = []
        self.source_cpp_files: list[str] = []
        self.source_hpp_files: list[str] = []

        if package_config:
            self.common_include_file = package_config.get(
                "common_include_file", self.common_include_file
            )
            self.exceptions = package_config.get("exceptions", self.exceptions)
            self.exclude_default_args = package_config.get(
                "exclude_default_args", self.exclude_default_args
            )
            self.source_cpp_patterns = package_config.get(
                "source_cpp_patterns", self.source_cpp_patterns
            )
            self.source_hpp_patterns = package_config.get(
                "source_hpp_patterns", self.source_hpp_patterns
            )

    @property
    def parent(self) -> None:
        """
        Returns None, as this is the top level of the info tree hierarchy.
        """
        return None

    def add_module(self, module_info: "ModuleInfo") -> None:
        """
        Add a module info object to the package.

        Parameters
        ----------
        module_info : ModuleInfo
            The module info object to add
        """
        self.module_collection.append(module_info)
        module_info.parent = self

    def init(self, restricted_paths: list[str]) -> None:
        """
        Initialise - collect header files and update info.

        Note: implementation (.cpp) files are not collected here. They are only
        needed for template instantiation discovery, which walks the source tree
        for them lazily (see collect_source_cpp) to avoid a second tree walk on
        every run when discovery is not used.

        Parameters
        ----------
        restricted_paths : list[str]
            A list of restricted paths to skip when collecting header files.
        """
        self.collect_source_headers(restricted_paths)
        self.update_from_source()

    def collect_source_files(
        self, patterns: list[str], restricted_paths: list[str]
    ) -> list[str]:
        """
        Collect files matching the given patterns from the source root.

        Walk through the source root and return any files matching the provided
        patterns e.g. "*.hpp", skipping restricted paths and generated wrapper
        files (e.g. .cppwg.hpp). The result is sorted by filename.

        Parameters
        ----------
        patterns : list[str]
            A list of filename patterns to match e.g. ["*.hpp"].
        restricted_paths : list[str]
            A list of restricted paths to skip when collecting files.

        Returns
        -------
        list[str]
            The collected file paths, sorted by filename.
        """
        filepaths: list[str] = []

        for root, _, filenames in os.walk(self.source_root, followlinks=True):
            for pattern in patterns:
                for filename in fnmatch.filter(filenames, pattern):
                    filepath = os.path.abspath(os.path.join(root, filename))

                    # Skip files in restricted paths
                    if any(
                        Path(restricted_path) in Path(filepath).parents
                        for restricted_path in restricted_paths
                    ):
                        continue

                    # Skip files with the extensions like .cppwg.hpp
                    suffix = os.path.splitext(os.path.splitext(filename)[0])[1]
                    if suffix == CPPWG_EXT:
                        continue

                    filepaths.append(filepath)

        # Sort by filename
        filepaths.sort(key=lambda x: os.path.basename(x))
        return filepaths

    def collect_source_headers(self, restricted_paths: list[str]) -> None:
        """
        Collect header files from the source root.

        Walk through the source root and add any files matching the source file
        patterns e.g. "*.hpp".

        Parameters
        ----------
        restricted_paths : list[str]
            A list of restricted paths to skip when collecting header files.
        """
        logger = logging.getLogger()

        self.source_hpp_files = self.collect_source_files(
            self.source_hpp_patterns, restricted_paths
        )

        # Check if any source files were found
        if not self.source_hpp_files:
            logger.error(f"No header files found in source root: {self.source_root}")
            raise FileNotFoundError()

    def collect_source_cpp(self, restricted_paths: list[str]) -> None:
        """
        Collect implementation files from the source root.

        Walk through the source root and add any files matching the source cpp
        patterns e.g. "*.cpp". These are scanned for explicit template
        instantiations when `discover_template_instantiations` is enabled; they
        are not added to the header collection.

        Parameters
        ----------
        restricted_paths : list[str]
            A list of restricted paths to skip when collecting files.
        """
        self.source_cpp_files = self.collect_source_files(
            self.source_cpp_patterns, restricted_paths
        )

    def update_from_source(self) -> None:
        """
        Update with data from the source headers.
        """
        for module_info in self.module_collection:
            module_info.update_from_source(self.source_hpp_files)

    def uses_template_discovery(self) -> bool:
        """
        Check whether any wrapped class needs template instantiation discovery.

        Discovery parses the source .cpp files with CastXML, which is expensive,
        so it is only worth doing if at least one class has discovery enabled and
        does not already have its template arguments set (directly or via
        `template_substitutions`).

        Returns
        -------
        bool
            True if template instantiation discovery should be run.
        """
        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                if class_info.excluded or class_info.template_arg_lists:
                    continue
                if class_info.hierarchy_attribute("discover_template_instantiations"):
                    return True
        return False

    def has_unresolved_template_classes(self) -> bool:
        """
        Check whether a templated, discovery-enabled class still lacks its args.

        Used to decide whether the CastXML/pygccxml discovery fallback is worth
        running after the source-text scan: it is only needed when a class that
        is actually templated (its header declares template parameters) and has
        discovery enabled still has no template arguments. Untemplated classes
        (which never receive template args) do not trigger the fallback.

        Returns
        -------
        bool
            True if the discovery fallback should be run.
        """
        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                if class_info.excluded or class_info.template_arg_lists:
                    continue
                if not class_info.hierarchy_attribute(
                    "discover_template_instantiations"
                ):
                    continue
                if class_info.template_params_from_source():
                    return True
        return False

    def update_template_instantiations(
        self, instantiation_map: dict[str, list[list[str]]]
    ) -> None:
        """
        Populate class template args from discovered explicit instantiations.

        Parameters
        ----------
        instantiation_map : dict[str, list[list[str]]]
            Map of base class name to the discovered template arg lists,
            e.g. {"Foo": [["2"], ["3"]]}.
        """
        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                class_info.apply_template_instantiations(instantiation_map)

    def update_from_ns(self, source_ns: "namespace_t") -> None:
        """
        Update modules with information from the parsed source namespace.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        for module_info in self.module_collection:
            module_info.update_from_ns(source_ns)

        self.resolve_exceptions(source_ns)

    def prune_uninstantiated_dependencies(self, restricted_paths: list[str]) -> None:
        """
        Drop wrapped instantiations that depend on an uninstantiated type.

        A class instantiation only has linkable symbols if it is explicitly
        instantiated. Two things instantiate a project template: it being wrapped
        (each wrapped ``cpp_name`` is emitted as ``template class X;`` in the
        header collection) and an explicit ``template class X;`` in a source .cpp
        file. Their union is the set of instantiations that will have symbols.

        If a wrapped method/constructor takes or returns a *project* template type
        (one sharing a base name with an instantiated class) that is not in that
        set - e.g. ``Facet<1>::GetFace`` returning the never-instantiated
        ``Facet<0>`` - the wrapper would fail to link/import, so that
        instantiation is dropped (per instantiation, so sibling instantiations of
        the same class survive) with a warning. Including source instantiations
        (not just wrapped ones) means a class curated out of wrapping but still
        instantiated in the source does not cause its wrapped siblings to be
        pruned.

        Library types (``std::vector<double>``, ``vtkSmartPointer<...>``, ...) do
        not share a base name with an instantiated class and are left alone. This
        is deliberately based on explicit instantiation rather than AST
        completeness: CastXML reports uninstantiated project templates as
        complete (it has the definition) and complete library templates as
        incomplete, so completeness is not a reliable signal.

        Parameters
        ----------
        restricted_paths : list[str]
            Paths to skip (e.g. the wrapper root) if the source .cpp files need
            to be collected to find explicit instantiations.
        """
        logger = logging.getLogger()

        # Instantiations that will have symbols: everything being wrapped ...
        instantiated = {
            cpp_name.replace(" ", "")
            for module_info in self.module_collection
            for class_info in module_info.class_collection
            for cpp_name in class_info.cpp_names
        }

        # ... plus everything explicitly instantiated in the source .cpp files
        # (which may include classes curated out of wrapping). Discovery may have
        # already collected these; if not, collect them now.
        if not self.source_cpp_files:
            self.collect_source_cpp(restricted_paths)
        for filepath in self.source_cpp_files:
            _, file_map = utils.find_template_instantiations_in_source_file(filepath)
            for name, arg_lists in file_map.items():
                for args in arg_lists:
                    full = f"{name}<{','.join(args)}>".replace(" ", "")
                    instantiated.add(full)

        project_bases = {
            name.split("<", 1)[0].split("::")[-1] for name in instantiated
        }

        query = access_type_matcher_t("public")

        def dependency(decl: "declarations.declaration_t") -> str | None:
            calldefs = list(decl.member_functions(function=query, allow_empty=True))
            calldefs += list(decl.constructors(function=query, allow_empty=True))
            for calldef in calldefs:
                types = list(calldef.argument_types)
                return_type = getattr(calldef, "return_type", None)
                if return_type is not None:
                    types.append(return_type)
                for arg_type in types:
                    for base, full in _referenced_instantiations(arg_type.decl_string):
                        if base in project_bases and full not in instantiated:
                            return full
            return None

        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                keep_cpp: list[str] = []
                keep_py: list[str] = []
                keep_decls: list["declarations.declaration_t"] = []
                for cpp_name, py_name, decl in zip(
                    class_info.cpp_names, class_info.py_names, class_info.decls
                ):
                    dep = dependency(decl)
                    if dep is not None:
                        logger.warning(
                            f"Excluding {cpp_name}: wrapped interface depends on "
                            f"uninstantiated type {dep}"
                        )
                        continue
                    keep_cpp.append(cpp_name)
                    keep_py.append(py_name)
                    keep_decls.append(decl)

                class_info.cpp_names = keep_cpp
                class_info.py_names = keep_py
                class_info.decls = keep_decls
                class_info.base_decls = [
                    base.related_class for decl in keep_decls for base in decl.bases
                ]

            # Drop classes left with no instantiations to wrap
            module_info.class_collection = [
                c for c in module_info.class_collection if c.cpp_names
            ]

    @staticmethod
    def parse_exception_entry(entry: Any) -> tuple[str, str]:
        """
        Return the (class name, message method) for an exceptions config entry.

        An entry may be a bare class name string, or a dict with a `name` and an
        optional `message_method` (defaulting to "what").

        Parameters
        ----------
        entry : Any
            A single entry from the `exceptions` config list.

        Returns
        -------
        tuple[str, str]
            The exception class name and the message accessor method name.
        """
        if isinstance(entry, dict):
            return entry["name"], entry.get("message_method", "what")
        return entry, "what"

    @property
    def exception_names(self) -> list[str]:
        """Return the names of the configured exception classes."""
        return [self.parse_exception_entry(entry)[0] for entry in self.exceptions]

    def resolve_exceptions(self, source_ns: "namespace_t") -> None:
        """
        Resolve exception config entries into translation data.

        For each entry in `exceptions`, look up the class in the source
        namespace, work out how to extract its message (calling the configured
        message_method, defaulting to what(), and adding .c_str() unless it
        already returns a pointer), and find which header declares it. The
        result is used to generate a pybind11 exception translator per module.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        logger = logging.getLogger()

        self.exception_info = []
        for entry in self.exceptions:
            name, message_method = self.parse_exception_entry(entry)

            class_decls = source_ns.classes(
                lambda decl: decl.name == name, allow_empty=True  # noqa: B023
            )

            if not class_decls:
                logger.error(f"Could not find exception class {name}.")
                raise RuntimeError(f"Could not find exception class: {name}")

            class_decl = class_decls[0]

            # Check the class (and its base classes, e.g. for an inherited
            # what()) actually declares the configured message method.
            method_decl = utils.find_member_function(class_decl, message_method)
            if method_decl is None:
                logger.error(f"Exception class {name} has no method {message_method}.")
                raise RuntimeError(
                    f"Exception class {name} has no method: {message_method}"
                )

            # PyErr_SetString needs a const char*. Add .c_str() unless the
            # message method already returns a pointer (e.g. what()).
            message_expr = f"e.{message_method}()"
            if not declarations.is_pointer(method_decl.return_type):
                message_expr += ".c_str()"

            self.exception_info.append(
                {
                    "cpp_type": name,
                    "message_expr": message_expr,
                    "source_file": os.path.basename(class_decl.location.file_name),
                }
            )
