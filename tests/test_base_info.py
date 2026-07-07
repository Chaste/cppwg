"""Unit tests for cppwg.info.base_info."""

from cppwg.info.class_info import CppClassInfo
from cppwg.info.module_info import ModuleInfo
from cppwg.info.package_info import PackageInfo


def test_gather_flat_flattens_list_option_across_hierarchy():
    """A list-valued option is gathered and flattened from class up to package.

    hierarchy_attribute_gather returns one (list) entry per hierarchy level;
    hierarchy_attribute_gather_flat merges them into a single list. This is what
    the writers rely on to collect exclude patterns (and is why consuming the
    un-flattened result directly used to crash).
    """
    package = PackageInfo("pkg", {"source_root": "/src"})
    module = ModuleInfo("mod")
    cls = CppClassInfo("Foo")
    package.add_module(module)
    module.add_class(cls)

    cls.arg_type_excludes = ["A", "B"]
    package.arg_type_excludes = ["C"]  # module level left empty

    # Nearest level first, then up the hierarchy.
    assert cls.hierarchy_attribute_gather_flat("arg_type_excludes") == ["A", "B", "C"]


def test_gather_flat_empty_when_unset():
    """An option set nowhere in the hierarchy yields an empty list, not a crash."""
    cls = CppClassInfo("Bar")
    assert cls.hierarchy_attribute_gather_flat("arg_type_excludes") == []


def test_gather_flat_treats_scalar_as_single_item():
    """A scalar (str) value is one item, not flattened character by character.

    Guards against a yaml `arg_type_excludes: double` (scalar) being expanded to
    ['d', 'o', 'u', 'b', 'l', 'e'] and mis-excluding unrelated calldefs.
    """
    cls = CppClassInfo("Foo")
    cls.arg_type_excludes = "double"

    assert cls.hierarchy_attribute_gather_flat("arg_type_excludes") == ["double"]


def test_gather_flat_treats_non_str_scalar_as_single_item():
    """Any non-sequence scalar is one item; only list/tuple/set are flattened."""
    cls = CppClassInfo("Foo")
    cls.arg_type_excludes = 5  # nonsensical but yaml-valid scalar

    assert cls.hierarchy_attribute_gather_flat("arg_type_excludes") == [5]
