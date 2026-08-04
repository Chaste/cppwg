"""Module information structure."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pygccxml import declarations

from cppwg.info.base_info import BaseInfo
from cppwg.info.class_info import CppClassInfo
from cppwg.info.enum_info import CppEnumInfo
from cppwg.info.free_function_info import CppFreeFunctionInfo
from cppwg.utils import utils

if TYPE_CHECKING:
    from pygccxml.declarations import declaration_t
    from pygccxml.declarations.namespace import namespace_t

    from cppwg.info.package_info import PackageInfo
    from cppwg.info.variable_info import CppVariableInfo


class ModuleInfo(BaseInfo):
    """
    A structure to hold information for individual modules.

    Attributes
    ----------
    external_bases : list[str]
        Names of base classes that are wrapped in a different package (and so are
        unknown to this cppwg run) but are registered by one of the modules in
        `imports`. A class in this module may inherit from a class named here.
        This is the cross-package counterpart to base classes wrapped in another
        module of the same package, which are detected automatically. Listing a
        base here is required (and is the only way) to inherit from an
        externally-package-wrapped base, so that cppwg never emits a base class
        it cannot confirm is registered. Names are matched without template
        arguments, e.g. `AbstractSphericalMesh` matches `AbstractSphericalMesh<2, 2>`.
    imports : list[str]
        Python modules to import at the start of this generated module, e.g. the
        compiled module of another package or sibling module whose classes are
        used here as base classes. Importing them ensures those base types are
        registered with pybind11 before this module's classes are registered.
        Setting this also enables referencing externally-wrapped base classes in
        class wrappers (see CppClassWrapperWriter), so that a class in this module
        can inherit from a class wrapped in another module (of this package, or
        of an imported package via `external_bases`). Do not list this module
        itself, to avoid a circular import.
    source_locations : list[str]
        A list of source locations for this module
    use_all_classes : bool
        Use all classes in the module
    use_all_free_functions : bool
        Use all free functions in the module
    use_all_variables : bool
        Use all variables in the module
    use_all_enums : bool
        Use all enums in the module

    package_info : PackageInfo
        The package info object this module belongs to

    class_collection : list[CppClassInfo]
        A list of class info objects that belong to this module
    free_function_collection : list[CppFreeFunctionInfo]
        A list of free function info objects that belong to this module
    variable_collection : list[CppVariableInfo]
        A list of variable info objects that belong to this module
    enum_collection : list[CppEnumInfo]
        A list of enum info objects that belong to this module
    """

    def __init__(self, name: str, module_config: dict[str, Any] | None = None) -> None:
        """
        Create a module info object from a module_config dict.

        Parameters
        ----------
        name : str
            The name of the module
        module_config : dict[str, Any]
            A dictionary of module configuration settings
        """
        super().__init__(name, module_config)

        self.external_bases: list[str] = []
        self.imports: list[str] = []
        self.source_locations: list[str] = []
        self.use_all_classes: bool = False
        self.use_all_free_functions: bool = False
        self.use_all_variables: bool = False
        self.use_all_enums: bool = False

        self.package_info: "PackageInfo | None" = None

        self.class_collection: list[CppClassInfo] = []
        self.free_function_collection: list[CppFreeFunctionInfo] = []
        self.variable_collection: list["CppVariableInfo"] = []
        self.enum_collection: list[CppEnumInfo] = []

        if module_config:
            for key in [
                "external_bases",
                "imports",
                "source_locations",
                "use_all_classes",
                "use_all_free_functions",
                "use_all_variables",
                "use_all_enums",
            ]:
                if key in module_config:
                    setattr(self, key, module_config[key])

    @property
    def parent(self) -> "PackageInfo":
        """
        Returns the package info object that holds this module info object.
        """
        return self.package_info

    @parent.setter
    def parent(self, package_info: "PackageInfo") -> None:
        """
        Set the package info object that holds this module.
        """
        self.package_info = package_info

    def add_class(self, class_info: CppClassInfo) -> None:
        """
        Add a class info object to the module.
        """
        self.class_collection.append(class_info)
        class_info.parent = self

    def add_free_function(self, free_function_info: CppFreeFunctionInfo) -> None:
        """
        Add a free function info object to the module.
        """
        self.free_function_collection.append(free_function_info)
        free_function_info.parent = self

    def add_variable(self, variable_info: "CppVariableInfo") -> None:
        """
        Add a variable info object to the module.
        """
        self.variable_collection.append(variable_info)
        variable_info.parent = self

    def add_enum(self, enum_info: CppEnumInfo) -> None:
        """
        Add an enum info object to the module.
        """
        self.enum_collection.append(enum_info)
        enum_info.parent = self

    def is_decl_in_source_path(self, decl: "declaration_t") -> bool:
        """
        Check if the declaration is associated with a file in the specified source paths.

        Parameters
        ----------
        decl : declaration_t
            The declaration to check

        Returns
        -------
        bool
            True if the declaration is associated with a file in a specified source path
        """
        if not self.source_locations:
            return True

        for location in self.source_locations:
            if Path(location) in Path(decl.location.file_name).parents:
                return True

        return False

    def sort_classes(self) -> None:
        """
        Order the class collection so each class comes after those it depends on.

        pybind11 requires a base class to be registered before any subclass, so
        a class must be emitted after every class it extends. A class whose
        public method or constructor signatures use another wrapped class is
        ordered after it too, but only where that does not contradict the
        inheritance order (which would otherwise create a cycle).

        The result is deterministic: it starts from an alphabetical baseline,
        breaks ties alphabetically, and matches base classes by name, so the
        registration order - and therefore the generated files - are stable from
        run to run. Requires the class ``decls``/``base_decls`` to be populated,
        so it must run after base-class discovery and pruning.
        """
        # Alphabetical baseline so the result does not depend on the order in
        # which classes were discovered or added.
        classes = sorted(self.class_collection, key=lambda c: c.name)
        if len(classes) < 2:
            self.class_collection = classes
            return

        # predecessors[c]: the classes that must be registered before c.
        predecessors: dict[CppClassInfo, set[CppClassInfo]] = {
            cls: set() for cls in classes
        }

        # Inheritance is a hard ordering constraint: a base precedes its
        # subclasses.
        for cls in classes:
            for other in classes:
                if other is not cls and cls.extends(other):
                    predecessors[cls].add(other)

        # Signature dependencies order a class after a wrapped type it uses,
        # unless that contradicts an inheritance ordering already recorded.
        # Argument type strings are gathered once per class to keep this cheap.
        arg_types = {cls: cls.signature_arg_types() for cls in classes}

        def requires(a: CppClassInfo, b: CppClassInfo) -> bool:
            return any(
                utils.type_string_matches(arg_type, b.name) for arg_type in arg_types[a]
            )

        for cls in classes:
            for other in classes:
                if other is cls or other in predecessors[cls]:
                    continue
                if cls in predecessors[other]:
                    continue  # inheritance already orders `other` after `cls`
                if requires(cls, other) and not requires(other, cls):
                    predecessors[cls].add(other)

        # Deterministic topological sort: repeatedly emit the alphabetically
        # first class whose predecessors have all been emitted. If a dependency
        # cycle stalls progress, emit the alphabetically first remaining class to
        # break it (a genuine inheritance cycle cannot occur in C++).
        ordered: list[CppClassInfo] = []
        emitted: set[CppClassInfo] = set()
        remaining = classes  # already alphabetical
        while remaining:
            pick = next(
                (cls for cls in remaining if predecessors[cls] <= emitted),
                remaining[0],
            )
            ordered.append(pick)
            emitted.add(pick)
            remaining = [cls for cls in remaining if cls is not pick]

        self.class_collection = ordered

    def update_from_ns(self, source_ns: "namespace_t") -> None:
        """
        Update module with information from the source namespace.

        Parameters
        ----------
        source_ns : pygccxml.declarations.namespace_t
            The source namespace
        """
        # Add discovered classes: if `use_all_classes` is True, this module
        # has no class info objects. Use class declarations from the
        # source namespace to create class info objects.
        if self.use_all_classes:
            class_decls = source_ns.classes(allow_empty=True)
            for class_decl in class_decls:
                if self.is_decl_in_source_path(class_decl):
                    class_info = CppClassInfo(class_decl.name)
                    class_info.update_names()
                    self.add_class(class_info)

        # Update classes with information from source namespace.
        for class_info in self.class_collection:
            class_info.update_from_ns(source_ns)

        # Classes are ordered by dependence later (PackageInfo.sort_classes),
        # once base-class discovery and pruning have finalised the wrapped set.

        # Add discovered free functions: if `use_all_free_functions` is True,
        # this module has no free function info objects. Use free function
        # decls from the source namespace to create free function info objects.
        if self.use_all_free_functions:
            free_functions = source_ns.free_functions(allow_empty=True)
            for free_function in free_functions:
                if self.is_decl_in_source_path(free_function):
                    ff_info = CppFreeFunctionInfo(free_function.name)
                    self.add_free_function(ff_info)

        # Update free functions with information from source namespace.
        for ff_info in self.free_function_collection:
            ff_info.update_from_ns(source_ns)

        # Add discovered enums: if `use_all_enums` is True, this module has no
        # enum info objects. Use enum decls from the source namespace to create
        # enum info objects.
        if self.use_all_enums:
            enum_decls = source_ns.enumerations(allow_empty=True)
            for enum_decl in enum_decls:
                # Skip enums nested in a class/struct: only namespace-scope enums
                # are wrapped standalone. A nested enum (e.g. `Value` in a
                # `struct Foo { enum Value {...}; }`) would be emitted with an
                # unqualified name that does not compile; the struct-enum special
                # case handles the wrapped-struct pattern.
                if declarations.is_class(enum_decl.parent):
                    continue
                if self.is_decl_in_source_path(enum_decl):
                    enum_info = CppEnumInfo(enum_decl.name)
                    self.add_enum(enum_info)

        # Update enums with information from source namespace.
        for enum_info in self.enum_collection:
            enum_info.update_from_ns(source_ns)

    def update_from_source(self, source_file_paths: list[str]) -> None:
        """
        Update module with information from the source headers.

        Parameters
        ----------
        source_files : list[str]
            A list of source file paths.
        """
        for class_info in self.class_collection:
            class_info.update_from_source(source_file_paths)

        self.class_collection.sort(key=lambda x: x.name)
        self.free_function_collection.sort(key=lambda x: x.name)
        self.enum_collection.sort(key=lambda x: x.name)
