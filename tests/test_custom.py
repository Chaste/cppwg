"""Unit tests for cppwg.templates.custom."""

from cppwg.templates.custom import Custom


def test_custom_hooks_return_defaults():
    """The base Custom generator's hooks return empty defaults."""
    custom = Custom()

    # Class-level hooks accept the class name (and any extra args) and default
    # to empty output.
    assert custom.get_class_cpp_pre_code("Foo_2_2") == ""
    assert custom.get_class_cpp_def_code("Foo_2_2") == ""
    assert custom.get_class_cpp_source_includes() == []

    # Module-level hooks default to empty output.
    assert custom.get_module_pre_code() == ""
    assert custom.get_module_code() == ""
