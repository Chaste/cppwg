"""Unit tests for cppwg.writers.base_writer."""

from cppwg.writers.base_writer import CppBaseWrapperWriter


def test_tidy_name_replaces_cpp_syntax():
    """A full C++ declaration is rewritten into a typedef-safe token."""
    writer = CppBaseWrapperWriter({})
    # Only the punctuation replacements are applied (not name_replacements).
    assert writer.tidy_name("::foo::bar<double, 2>") == "_foo_bar_lt_double_2_gt_"


def test_tidy_name_handles_pointers_refs_and_negatives():
    """Each punctuation replacement in the tidy map is applied."""
    writer = CppBaseWrapperWriter({})
    assert writer.tidy_name("Foo *") == "FooPtr"
    assert writer.tidy_name("Foo &") == "FooRef"
    assert writer.tidy_name("Foo<-1>") == "Foo_lt_neg1_gt_"
