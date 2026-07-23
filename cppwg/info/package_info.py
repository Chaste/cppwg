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

# Matches the (possibly qualified) name that introduces a template-id, i.e. an
# identifier immediately followed by "<".
_TEMPLATE_ID_NAME_RE = re.compile(r"[A-Za-z_][\w:]*(?=<)")

# A namespace qualifier, e.g. the "ns::" in "ns::Foo" or "boost::" in
# "boost::shared_ptr". Used to reduce a name to its unqualified form.
_NAMESPACE_QUALIFIER_RE = re.compile(r"[A-Za-z_]\w*::")

# A bare C++ identifier. Used to pull candidate type names out of a type's
# decl_string when resolving auto-includes; non-project identifiers (namespaces,
# library types, keywords) simply do not resolve against the project map.
_IDENTIFIER_RE = re.compile(r"[A-Za-z_]\w*")


def _strip_namespace_qualifiers(name: str) -> str:
    """
    Remove namespace qualifiers (and whitespace) from a template-id.

    e.g. "::ns::Foo<ns::Bar<2>, 3>" -> "Foo<Bar<2>,3>". Reducing both a
    referenced type and the instantiated set to this unqualified, space-free form
    lets them be compared consistently: cpp_names and source-scanned
    instantiations are unqualified, while a pygccxml decl_string keeps its
    namespace, so a qualified dependency would otherwise never match.
    """
    return _NAMESPACE_QUALIFIER_RE.sub("", name.replace(" ", "")).lstrip(":")


def _referenced_instantiations(decl_string: str) -> "Iterator[tuple[str, str]]":
    """
    Yield (unqualified base, normalised full name) for template-ids in a type.

    Every template-id is yielded, at every nesting level, so a nested type does
    not hide an enclosing one: "boost::shared_ptr<PottsMesh<2>>" yields both
    ("shared_ptr", "shared_ptr<PottsMesh<2>>") and ("PottsMesh", "PottsMesh<2>").
    The closing ">" is found by matching angle brackets on depth rather than with
    a "[^<>]*" argument list that could not span a nested "<...>".
    e.g. "::Facet<0> *" -> ("Facet", "Facet<0>");
    "std::vector<double>" -> ("vector", "vector<double>").

    Both the base and the full name are unqualified (namespace qualifiers
    stripped) so they compare consistently with the unqualified cpp_names and
    source-scanned instantiations that pruning holds.

    Parameters
    ----------
    decl_string : str
        A pygccxml type declaration string.

    Yields
    ------
    tuple[str, str]
        The unqualified base class name and the whitespace-stripped full name.
    """
    length = len(decl_string)
    for match in _TEMPLATE_ID_NAME_RE.finditer(decl_string):
        depth = 0
        close_index = None
        for index in range(match.end(), length):
            if decl_string[index] == "<":
                depth += 1
            elif decl_string[index] == ">":
                depth -= 1
                if depth == 0:
                    close_index = index
                    break
        if close_index is None:
            continue
        full = _strip_namespace_qualifiers(decl_string[match.start() : close_index + 1])
        base = full.split("<", 1)[0]
        yield base, full


if TYPE_CHECKING:
    from pygccxml.declarations.namespace import namespace_t

    from cppwg.info.class_info import CppClassInfo
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
    typecasters : list[dict[str, Any]]
        Type-caster headers to auto-include per class wrapper. Each entry is a
        dict with a `header` (the caster filename, e.g. `caster_petsc.h`) and a
        list of `types` (C++ type names it handles, e.g. ["Vec", "Mat"]). When a
        class's wrapped interface uses one of those types, cppwg adds the header
        to that class's wrapper .cpp.

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

    def __init__(self, name: str, package_config: dict[str, Any] | None = None) -> None:
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
        self.typecasters: list[dict[str, Any]] = []
        # Validated (header, types) tuples parsed from self.typecasters, computed
        # once on first access. None until then; see parsed_typecasters.
        self._parsed_typecasters: "list[tuple[str, list[str]]] | None" = None

        self.exception_info: list[dict[str, str]] = []
        self.module_collection: list["ModuleInfo"] = []
        self.source_cpp_files: list[str] = []
        # Explicit instantiations found only via the CastXML macro fallback during
        # discovery (e.g. "Foo<2,2>"), which the source-text scan cannot see. Held
        # so pruning counts a macro-instantiated type as instantiated even when it
        # is curated out of wrapping. Normalized (no spaces), like cpp_names.
        self.macro_instantiations: set[str] = set()
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
            self.typecasters = package_config.get("typecasters", self.typecasters)

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
        files (e.g. .cppwg.hpp). The result is sorted by filename, then by full
        path, giving a deterministic order even when a basename is shared.

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

        # Sort by filename, then by full path as a tie-break so that files
        # sharing a basename in different directories (e.g. multiple Foo.cpp) get
        # a deterministic total order. os.walk order is filesystem-dependent, so
        # sorting on the basename alone would otherwise leave such ties in an
        # unstable order and make downstream wrapper generation non-reproducible.
        filepaths.sort(key=lambda x: (os.path.basename(x), x))
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

        Discovery walks the source tree for the .cpp files and scans them, which
        is expensive, so it is only worth doing if at least one class has
        discovery enabled, does not already have its template arguments set
        (directly or via `template_substitutions`), and is actually templated -
        only a templated class can receive discovered template arguments. A class
        whose templated-ness cannot be determined (no resolved header path) is
        treated conservatively as possibly templated so discovery still runs.

        Returns
        -------
        bool
            True if template instantiation discovery should be run.
        """
        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                if class_info.excluded or class_info.template_arg_lists:
                    continue
                if not class_info.hierarchy_attribute(
                    "discover_template_instantiations"
                ):
                    continue
                # Skip a class known to be untemplated (its header is available
                # and declares no template parameters); it can never receive
                # discovered args, so it alone should not trigger the .cpp scan.
                if class_info.source_file_path and not (
                    class_info.template_params_from_source()
                ):
                    continue
                return True
        return False

    def update_template_instantiations(
        self,
        instantiation_map: dict[str, list[list[str]]],
        merge: bool = False,
        trust_defaulted_args: bool = True,
    ) -> None:
        """
        Populate class template args from discovered explicit instantiations.

        Parameters
        ----------
        instantiation_map : dict[str, list[list[str]]]
            Map of base class name to the discovered template arg lists,
            e.g. {"Foo": [["2"], ["3"]]}.
        merge : bool
            If True, merge the arg lists into a class's already
            discovery-discovered args (rather than only setting args for classes
            that have none). Used for the CastXML fallback so macro instantiations
            add to text-scanned ones. `template_substitutions` are never extended.
        trust_defaulted_args : bool
            Whether the source of these arg lists renders defaulted trailing
            template arguments reliably (CastXML >= 0.6.0). When False, a merge is
            skipped for a class with defaulted template parameters to avoid adding
            a differently-rendered duplicate instantiation.
        """
        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                class_info.apply_template_instantiations(
                    instantiation_map,
                    merge=merge,
                    trust_defaulted_args=trust_defaulted_args,
                )

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

    def sort_classes(self) -> None:
        """
        Order each module's classes so a base class precedes its subclasses.

        Must run after base-class discovery and pruning, once every class's
        declarations are final, so the inheritance ordering is complete.
        """
        for module_info in self.module_collection:
            module_info.sort_classes()

    def discover_base_class_instantiations(self, source_ns: "namespace_t") -> None:
        """
        Discover instantiations of opted-in templated classes from base classes.

        A templated class that is never explicitly instantiated - e.g. an
        abstract base only ever used as a base class or through pointers - leaves
        no ``template class X<...>;`` for the source scan or the CastXML macro
        fallback to find. But it is implicitly instantiated wherever a wrapped
        concrete class derives from it, so it appears (at the right template
        arguments) among that class's base declarations. Harvest those
        instantiations for any opted-in, still-unresolved templated class, so
        such bases can be wrapped without hand-written template_substitutions.

        A harvested arg list is adopted only when its length matches the class's
        template parameter count. This guards against a CastXML version that
        collapses a defaulted trailing argument (naming e.g.
        ``AbstractLinearPde<2, 2>`` as ``AbstractLinearPde<2>``): the collapsed
        list is rejected and the class is left for template_substitutions.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace.
        """
        logger = logging.getLogger()

        # Opted-in, templated classes that discovery has not yet resolved.
        targets: dict[str, "CppClassInfo"] = {}
        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                if class_info.excluded or class_info.template_arg_lists:
                    continue
                if not class_info.hierarchy_attribute(
                    "discover_template_instantiations"
                ):
                    continue
                if class_info.template_params_from_source():
                    targets[class_info.name] = class_info

        if not targets:
            return

        # Harvest instantiation args (and the matching decl) from the base
        # classes of every already-wrapped class.
        harvested: dict[str, list[list[str]]] = {name: [] for name in targets}
        base_decl_for: dict[tuple, Any] = {}
        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                for decl in class_info.decls:
                    try:
                        bases = decl.recursive_bases
                    except Exception:  # noqa: BLE001 - pygccxml raises on odd types
                        continue
                    for base in bases:
                        base_decl = base.related_class
                        if (
                            base_decl is None
                            or not declarations.templates.is_instantiation(
                                base_decl.name
                            )
                        ):
                            continue
                        base_name, args = declarations.templates.split(base_decl.name)
                        name = base_name.split("::")[-1]
                        if name not in targets or not args:
                            continue
                        args = [arg.strip() for arg in args]
                        key = (name, tuple(args))
                        if key in base_decl_for:
                            continue
                        base_decl_for[key] = base_decl
                        harvested[name].append(args)

        # Adopt the harvested instantiations, guarded by parameter count.
        for name, arg_lists in harvested.items():
            class_info = targets[name]
            param_count = len(class_info.template_params_from_source())
            valid = [args for args in arg_lists if len(args) == param_count]
            # Drop base-harvested instantiations excluded by discover_arg_excludes
            # (e.g. a spatial dimension of 1), consistent with source discovery.
            valid = class_info.filter_discovered_instantiations(valid)
            if not valid:
                continue

            class_info.template_arg_lists = valid
            class_info.update_names()
            class_info.decls = [base_decl_for[(name, tuple(a))] for a in valid]
            class_info.base_decls = [
                base.related_class for decl in class_info.decls for base in decl.bases
            ]
            logger.info(
                f"Discovered {len(valid)} instantiation(s) of {name} from base "
                "classes"
            )

    @staticmethod
    def _iter_wrapped_arg_return_types(
        class_info: "CppClassInfo", decl: Any
    ) -> "Iterator[declarations.type_t]":
        """
        Yield the arg/return types the writers will actually wrap for a class.

        Walks the public member functions and constructors of ``decl`` and yields
        the pygccxml type of every argument and return type that survives the same
        config-driven exclusions the writers apply (``excluded_methods``,
        ``return_type_excludes``, ``arg_type_excludes``,
        ``constructor_arg_type_excludes``, ``constructor_signature_excludes``,
        ``calldef_excludes``, iterator-argument and abstract-class-constructor
        skips). A type reached only through an excluded method or constructor is
        never yielded, so callers see exactly the types that end up in the
        generated wrapper. Shared by dependency pruning and auto-include
        resolution so the two cannot diverge from the writers.

        Parameters
        ----------
        class_info : CppClassInfo
            The class whose exclusion config to honour.
        decl : pygccxml.declarations.class_t
            The class declaration to walk.

        Yields
        ------
        pygccxml.declarations.type_t
            Each wrapped argument or return type.
        """
        query = access_type_matcher_t("public")
        gather = class_info.hierarchy_attribute_gather_flat
        calldef_excludes = gather("calldef_excludes")
        return_type_excludes = gather("return_type_excludes") + calldef_excludes
        arg_type_excludes = gather("arg_type_excludes") + calldef_excludes
        ctor_arg_type_excludes = arg_type_excludes + gather(
            "constructor_arg_type_excludes"
        )
        ctor_signature_excludes = gather("constructor_signature_excludes")
        excluded_methods = class_info.excluded_methods or []

        def excluded(type_string: str, patterns: list[str]) -> bool:
            return any(
                utils.type_string_matches(type_string, pattern) for pattern in patterns
            )

        def signature_excluded(arg_strings: list[str]) -> bool:
            # A constructor is excluded when a constructor_signature_excludes
            # entry has the same arity and each argument matches its positional
            # pattern (matching the constructor writer).
            for exclude_types in ctor_signature_excludes:
                if not isinstance(exclude_types, (list, tuple)):
                    continue
                if len(exclude_types) != len(arg_strings):
                    continue
                if all(
                    utils.type_string_matches(arg_string, exclude_type)
                    for arg_string, exclude_type in zip(arg_strings, exclude_types)
                ):
                    return True
            return False

        for method in decl.member_functions(function=query, allow_empty=True):
            if method.name in excluded_methods:
                continue
            return_type = method.return_type
            if return_type is not None and excluded(
                return_type.decl_string, return_type_excludes
            ):
                continue
            if any(
                excluded(arg.decl_string, arg_type_excludes)
                for arg in method.argument_types
            ):
                continue
            yield from method.argument_types
            if return_type is not None:
                yield return_type

        # Constructors are not wrapped for an abstract class that inherits from an
        # abstract base (matching the constructor writer), so its constructor
        # arguments cannot introduce a dependency. A base whose related_class is
        # None could not be resolved by pygccxml; treat it as non-abstract (skip
        # it) rather than dereferencing None.
        ctors_wrapped = not (
            decl.is_abstract
            and any(
                base.related_class is not None and base.related_class.is_abstract
                for base in decl.recursive_bases
            )
        )
        if ctors_wrapped:
            for ctor in decl.constructors(function=query, allow_empty=True):
                arg_strings = [arg.decl_string for arg in ctor.argument_types]
                if any("iterator" in s.lower() for s in arg_strings):
                    continue
                if any(excluded(s, ctor_arg_type_excludes) for s in arg_strings):
                    continue
                if signature_excluded(arg_strings):
                    continue
                yield from ctor.argument_types

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

        Only members that would actually be wrapped are considered, applying the
        same config-driven exclusions the writers apply (``excluded_methods``,
        ``return_type_excludes``, ``arg_type_excludes``,
        ``constructor_arg_type_excludes``, ``constructor_signature_excludes``,
        ``calldef_excludes``, and abstract-class constructors). A type reached
        only through an excluded method or constructor is never emitted and does
        not trigger a drop.

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
        # Names are reduced to their unqualified form so they compare with the
        # (also unqualified) referenced types from _referenced_instantiations.
        instantiated = {
            _strip_namespace_qualifiers(cpp_name)
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
                    full = f"{name}<{','.join(args)}>"
                    instantiated.add(_strip_namespace_qualifiers(full))

        # ... plus macro-generated explicit instantiations. The text scan above
        # cannot see these (find_template_instantiations_in_source_file yields an
        # empty map for a macro-only file), so a class instantiated only via a
        # macro - even one curated out of wrapping - would otherwise look
        # uninstantiated and wrongly prune its dependents. Discovery recovers them
        # from the parsed AST and records them here.
        instantiated |= {
            _strip_namespace_qualifiers(name) for name in self.macro_instantiations
        }

        project_bases = {name.split("<", 1)[0] for name in instantiated}

        def uninstantiated(arg_type: "declarations.type_t") -> str | None:
            for base, full in _referenced_instantiations(arg_type.decl_string):
                if base in project_bases and full not in instantiated:
                    return full
            return None

        def dependency(class_info: "CppClassInfo", decl) -> str | None:
            # Only the arg/return types that will actually be wrapped can
            # introduce a dependency; _iter_wrapped_arg_return_types honours the
            # same config-driven exclusions the writers apply, so a type reached
            # only through an excluded method/constructor is never considered.
            for arg_type in self._iter_wrapped_arg_return_types(class_info, decl):
                dep = uninstantiated(arg_type)
                if dep is not None:
                    return dep
            return None

        for module_info in self.module_collection:
            for class_info in module_info.class_collection:
                # template_arg_lists is parallel to cpp_names for a templated
                # class (empty for an untemplated one) and is indexed by position
                # elsewhere (e.g. the writers substitute template params in
                # default arguments), so it must be pruned in lockstep.
                has_template_args = bool(class_info.template_arg_lists)

                keep_cpp: list[str] = []
                keep_py: list[str] = []
                keep_decls: list["declarations.declaration_t"] = []
                keep_args: list[list[Any]] = []
                for index, (cpp_name, py_name, decl) in enumerate(
                    zip(class_info.cpp_names, class_info.py_names, class_info.decls)
                ):
                    dep = dependency(class_info, decl)
                    if dep is not None:
                        logger.warning(
                            f"Excluding {cpp_name}: wrapped interface depends on "
                            f"uninstantiated type {dep}"
                        )
                        continue
                    keep_cpp.append(cpp_name)
                    keep_py.append(py_name)
                    keep_decls.append(decl)
                    if has_template_args:
                        keep_args.append(class_info.template_arg_lists[index])

                class_info.cpp_names = keep_cpp
                class_info.py_names = keep_py
                class_info.decls = keep_decls
                if has_template_args:
                    class_info.template_arg_lists = keep_args
                class_info.base_decls = [
                    base.related_class for decl in keep_decls for base in decl.bases
                ]

            # Drop classes left with no instantiations to wrap
            module_info.class_collection = [
                c for c in module_info.class_collection if c.cpp_names
            ]

    def _module_source_locations(self) -> list[Path]:
        """
        Return the source-location paths that scope the wrapped source tree.

        A module with no ``source_locations`` wraps everything, so it contributes
        the source root; this is decided per module so one module restricting its
        locations does not narrow the scope for a module that wraps everything.
        Mirrors the scoping used by log_unknown_classes.

        Returns
        -------
        list[pathlib.Path]
            The directories that bound the project's own source files.
        """
        locations: list[Path] = []
        for module_info in self.module_collection:
            if module_info.source_locations:
                locations.extend(Path(loc) for loc in module_info.source_locations)
            else:
                locations.append(Path(self.source_root))
        return locations

    def _build_type_header_map(self) -> dict[str, str]:
        """
        Map each project class name to the header basename that defines it.

        Builds ``{class name: header}`` by scanning the project's own header files
        (restricted to the module source locations, so library headers pulled in
        transitively are excluded) for class/struct definitions. The header text
        is used - rather than the parsed namespace - because a templated class's
        *instantiation* decl reports its location as the point of instantiation
        (the generated header collection), not the header that defines the
        template; scanning the source finds every class at its definition site,
        templated or not, wrapped or not. A name that resolves to more than one
        distinct header is ambiguous and dropped, so an auto-include is never
        guessed wrongly - such a type must be added via source_includes.

        Returns
        -------
        dict[str, str]
            Map of class name to defining header basename.
        """
        source_locations = self._module_source_locations()

        def in_source_locations(file_path: str) -> bool:
            parents = Path(file_path).parents
            return any(location in parents for location in source_locations)

        mapping: dict[str, str] = {}
        ambiguous: set[str] = set()
        for hpp_file_path in self.source_hpp_files:
            if not in_source_locations(hpp_file_path):
                continue
            header = os.path.basename(hpp_file_path)
            for _, class_name, _ in utils.find_classes_in_source_file(hpp_file_path):
                name = class_name.strip()
                if not name:
                    continue
                existing = mapping.get(name)
                if existing is None:
                    mapping[name] = header
                elif existing != header:
                    ambiguous.add(name)

        for name in ambiguous:
            mapping.pop(name, None)
        return mapping

    def resolve_auto_includes(self) -> None:
        """
        Resolve project-type headers for classes with auto_includes enabled.

        For each wrapped class that opts into ``auto_includes``, inspect the types
        its wrapped methods/constructors actually expose (via
        _iter_wrapped_arg_return_types, so exclusions are honoured) plus the
        project types named as its template arguments (e.g. ``Foo<Bar, DIM>``),
        resolve any that name a project class to that class's header, and record
        the headers on ``class_info.auto_include_headers`` for the writer to emit.
        The class's own header is dropped (the writer always includes it), as is
        anything that does not resolve to a project header (library types are left alone).

        A class using ``common_include_file`` is skipped: the common header
        already includes every project header, so per-type includes are moot.

        Must run after the wrapped set is final (post pruning/sorting) so the
        resolved headers reflect exactly what will be wrapped.
        """
        # Nothing to do unless some wrapped class opts in.
        opted_in = [
            class_info
            for module_info in self.module_collection
            for class_info in module_info.class_collection
            if not class_info.excluded
            and class_info.hierarchy_attribute("auto_includes")
            and not class_info.hierarchy_attribute("common_include_file")
        ]
        if not opted_in:
            return

        type_header_map = self._build_type_header_map()

        for class_info in opted_in:
            headers: set[str] = set()
            for decl in class_info.decls:
                for arg_type in self._iter_wrapped_arg_return_types(class_info, decl):
                    for name in _IDENTIFIER_RE.findall(arg_type.decl_string):
                        header = type_header_map.get(name)
                        if header:
                            headers.add(header)

            # Project types named as template arguments of this class's
            # instantiations (e.g. Foo<Bar, DIM>) are dependencies the generated
            # code needs even if they never appear in a wrapped signature, so
            # resolve their headers here too. Numeric args (dimensions like 2
            # or 3) and library types resolve to nothing.
            for arg_list in class_info.template_arg_lists:
                for arg in arg_list:
                    for name in _IDENTIFIER_RE.findall(str(arg)):
                        header = type_header_map.get(name)
                        if header:
                            headers.add(header)

            # The writer always includes the class's own header; drop it here.
            own_header = class_info.source_file
            if not own_header and class_info.decls:
                own_header = os.path.basename(class_info.decls[0].location.file_name)
            headers.discard(own_header)

            class_info.auto_include_headers = sorted(headers)

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

    @property
    def parsed_typecasters(self) -> "list[tuple[str, list[str]]]":
        """
        Return the validated typecasters as (header, types) tuples.

        `parse_typecaster_entry` logs a warning for each malformed entry. Wrapper
        generation checks the typecasters for every class, so parsing per class
        would repeat those warnings once per class and drown out other output.
        Parse the config list once here (warning at most once per bad entry) and
        cache the result, so the class writers iterate an already-validated list.

        Returns
        -------
        list[tuple[str, list[str]]]
            The validated (header, types) tuples, in config order.
        """
        if self._parsed_typecasters is None:
            parsed: list[tuple[str, list[str]]] = []
            for entry in self.typecasters:
                result = self.parse_typecaster_entry(entry)
                if result is not None:
                    parsed.append(result)
            self._parsed_typecasters = parsed
        return self._parsed_typecasters

    @staticmethod
    def parse_typecaster_entry(entry: Any) -> "tuple[str, list[str]] | None":
        """
        Return the (header, types) for a typecasters config entry, or None.

        A valid entry is a dict with a non-empty string `header` and a `types`
        list of non-empty type-name strings, e.g.
        `{"header": "caster_petsc.h", "types": ["Vec", "Mat"]}`. The header is
        stripped of surrounding whitespace; each type is whitespace-normalized
        with `utils.canonicalize_type_whitespace` (the same normalization
        `type_string_matches` applies), so a padded value like `" Vec "` is
        stored as `"Vec"` and a blank type is dropped rather than kept as a
        never-matching entry (matching stays token- and case-sensitive). A
        malformed entry (not a dict, missing/blank header, or no usable types)
        is skipped with a warning rather than aborting generation.

        Parameters
        ----------
        entry : Any
            A single entry from the `typecasters` config list.

        Returns
        -------
        tuple[str, list[str]] | None
            The caster header filename and its list of type names, or None if
            the entry is malformed.
        """
        logger = logging.getLogger()

        if not isinstance(entry, dict):
            logger.warning(
                f"Ignoring malformed typecasters entry (not a dict): {entry!r}"
            )
            return None

        header = entry.get("header")
        if isinstance(header, str):
            header = header.strip()
        if not isinstance(header, str) or not header:
            logger.warning(f"Ignoring typecasters entry with no header: {entry!r}")
            return None

        raw_types = entry.get("types")
        if isinstance(raw_types, str):
            raw_types = [raw_types]
        elif not isinstance(raw_types, (list, tuple)):
            raw_types = []
        # Normalize each type the same way matching does (utils.type_string_matches
        # canonicalizes both sides), so the stored value matches what scanning
        # compares against and a blank type is dropped rather than kept as a
        # never-matching entry.
        types = []
        for t in raw_types:
            if not isinstance(t, str):
                continue
            normalized = utils.canonicalize_type_whitespace(t)
            if normalized:
                types.append(normalized)

        if not types:
            logger.warning(
                f"Ignoring typecasters entry for {header!r} with no valid types."
            )
            return None

        return header, types

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
