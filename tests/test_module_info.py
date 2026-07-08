"""Unit tests for cppwg.info.module_info."""

from types import SimpleNamespace

from cppwg.info.class_info import CppClassInfo
from cppwg.info.module_info import ModuleInfo


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
