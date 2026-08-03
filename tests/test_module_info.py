"""Unit tests for cppwg.info.module_info."""

from types import SimpleNamespace

from cppwg.info.class_info import CppClassInfo
from cppwg.info.enum_info import CppEnumInfo
from cppwg.info.free_function_info import CppFreeFunctionInfo
from cppwg.info.module_info import ModuleInfo
from cppwg.info.variable_info import CppVariableInfo


def _class(name: str, base_names: tuple[str, ...] = ()) -> CppClassInfo:
    """
    Build a minimal class info with the given base class names.

    base_decls are stand-ins carrying just a ``name`` (as pygccxml exposes),
    which is what the name-based inheritance matching uses. decls is left empty
    so there are no signature dependencies to consider.
    """
    cls = CppClassInfo(name)
    cls.base_decls = [SimpleNamespace(name=base) for base in base_names]
    cls.decls = []
    return cls


def test_sort_classes_orders_base_before_subclasses():
    """A base class is registered before subclasses that sort ahead of it.

    AbstractLinearEllipticPde/ParabolicPde sort alphabetically before their
    base AbstractLinearPde, so a naive alphabetical order would register the
    subclasses first and fail to import. The base is matched by name even though
    the base decls carry template arguments (AbstractLinearPde<1, 1>).
    """
    module = ModuleInfo("all")
    module.class_collection = [
        _class("AbstractLinearEllipticPde", ("AbstractLinearPde<1, 1>",)),
        _class("AbstractLinearParabolicPde", ("AbstractLinearPde<1, 1>",)),
        _class("AbstractLinearPde"),
    ]

    module.sort_classes()

    order = [c.name for c in module.class_collection]
    assert order.index("AbstractLinearPde") < order.index("AbstractLinearEllipticPde")
    assert order.index("AbstractLinearPde") < order.index("AbstractLinearParabolicPde")


def test_sort_classes_orders_transitive_inheritance():
    """Ordering respects a multi-level hierarchy (Grandchild -> Child -> Base)."""
    module = ModuleInfo("all")
    module.class_collection = [
        _class("Child", ("Base",)),
        _class("Grandchild", ("Child",)),
        _class("Base"),
    ]

    module.sort_classes()

    order = [c.name for c in module.class_collection]
    assert order == ["Base", "Child", "Grandchild"]


def test_sort_classes_is_deterministic_and_alphabetical_without_dependencies():
    """Independent classes keep alphabetical order regardless of input order."""
    module = ModuleInfo("all")
    module.class_collection = [_class(n) for n in ("Zebra", "Apple", "Mango")]

    module.sort_classes()
    assert [c.name for c in module.class_collection] == ["Apple", "Mango", "Zebra"]

    # Re-sorting from a different input order yields the same result (stable).
    module.class_collection = list(reversed(module.class_collection))
    module.sort_classes()
    assert [c.name for c in module.class_collection] == ["Apple", "Mango", "Zebra"]


def test_sort_classes_stable_for_sibling_subclasses():
    """Sibling subclasses of a common base keep alphabetical order among themselves."""
    module = ModuleInfo("all")
    module.class_collection = [
        _class("Beta", ("Base",)),
        _class("Alpha", ("Base",)),
        _class("Base"),
    ]

    module.sort_classes()

    order = [c.name for c in module.class_collection]
    assert order == ["Base", "Alpha", "Beta"]


def _decl(name, file_name):
    """A minimal declaration stand-in with a name and source location."""
    return SimpleNamespace(name=name, location=SimpleNamespace(file_name=file_name))


def test_add_variable_sets_parent():
    module = ModuleInfo("mod")
    var = CppVariableInfo("my_var")
    module.add_variable(var)
    assert module.variable_collection == [var]
    assert var.parent is module


def test_is_decl_in_source_path_without_locations():
    """With no source_locations, every declaration is in scope."""
    module = ModuleInfo("mod")
    assert module.is_decl_in_source_path(_decl("Foo", "/anywhere/Foo.hpp")) is True


def test_is_decl_in_source_path_with_locations():
    """A declaration is in scope only under one of the source_locations."""
    module = ModuleInfo("mod", {"source_locations": ["/src/wanted"]})
    assert module.is_decl_in_source_path(_decl("Foo", "/src/wanted/Foo.hpp")) is True
    assert module.is_decl_in_source_path(_decl("Bar", "/src/other/Bar.hpp")) is False


def test_update_from_ns_discovers_all_classes_and_functions(monkeypatch):
    """use_all_* discovers in-scope decls and delegates the per-item update."""
    monkeypatch.setattr(CppClassInfo, "update_from_ns", lambda self, ns: None)
    monkeypatch.setattr(CppFreeFunctionInfo, "update_from_ns", lambda self, ns: None)
    monkeypatch.setattr(CppEnumInfo, "update_from_ns", lambda self, ns: None)

    module = ModuleInfo(
        "mod",
        {
            "use_all_classes": True,
            "use_all_free_functions": True,
            "use_all_enums": True,
            "source_locations": ["/src"],
        },
    )
    source_ns = SimpleNamespace(
        classes=lambda allow_empty=True: [_decl("Foo", "/src/Foo.hpp")],
        free_functions=lambda allow_empty=True: [_decl("my_func", "/src/f.hpp")],
        # One in-scope enum is discovered; one outside source_locations is dropped.
        enumerations=lambda allow_empty=True: [
            _decl("MyEnum", "/src/e.hpp"),
            _decl("Outside", "/other/e.hpp"),
        ],
    )

    module.update_from_ns(source_ns)

    assert [c.name for c in module.class_collection] == ["Foo"]
    assert [f.name for f in module.free_function_collection] == ["my_func"]
    assert [e.name for e in module.enum_collection] == ["MyEnum"]


def test_update_from_source_updates_then_sorts(monkeypatch):
    """Each class is updated from source, then classes are sorted by name."""
    updated = []
    monkeypatch.setattr(
        CppClassInfo,
        "update_from_source",
        lambda self, paths: updated.append(self.name),
    )

    module = ModuleInfo("mod")
    module.add_class(CppClassInfo("Zebra"))
    module.add_class(CppClassInfo("Apple"))

    module.update_from_source(["/src/x.hpp"])

    assert updated == ["Zebra", "Apple"]  # updated in insertion order, before sorting
    assert [c.name for c in module.class_collection] == ["Apple", "Zebra"]


def test_sort_classes_single_class_is_a_noop():
    """A module with fewer than two classes needs no ordering."""
    module = ModuleInfo("mod")
    module.add_class(_class("Only"))
    module.sort_classes()
    assert [c.name for c in module.class_collection] == ["Only"]


def test_update_from_ns_skips_decls_outside_source_path(monkeypatch):
    """Discovered decls outside the module's source_locations are not added."""
    monkeypatch.setattr(CppClassInfo, "update_from_ns", lambda self, ns: None)
    monkeypatch.setattr(CppFreeFunctionInfo, "update_from_ns", lambda self, ns: None)

    module = ModuleInfo(
        "mod", {"use_all_classes": True, "source_locations": ["/wanted"]}
    )
    source_ns = SimpleNamespace(
        classes=lambda allow_empty=True: [_decl("Foo", "/other/Foo.hpp")],
        free_functions=lambda allow_empty=True: [],
    )

    module.update_from_ns(source_ns)

    assert module.class_collection == []  # out-of-path discovery is dropped
