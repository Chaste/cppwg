"""Unit tests for cppwg.writers.base_writer."""

from types import SimpleNamespace

from cppwg.writers.base_writer import CppBaseWrapperWriter


def _arg(name, default_value=None, decl_type="int"):
    return SimpleNamespace(name=name, default_value=default_value, decl_type=decl_type)


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


def test_render_default_args_keyword_and_value():
    """A default value is normalised and appended; exclude keeps only the name."""
    writer = CppBaseWrapperWriter({})
    args = [_arg("count", default_value="(-1)", decl_type="int")]
    assert writer.render_default_args(args, exclude_default_args=False) == (
        ', py::arg("count") = -1'
    )
    assert writer.render_default_args(args, exclude_default_args=True) == (
        ', py::arg("count")'
    )
    # No default value -> a bare py::arg.
    assert writer.render_default_args([_arg("x")], exclude_default_args=False) == (
        ', py::arg("x")'
    )


def test_render_default_args_substitutes_template_params():
    """A default referencing a class template param is substituted; others are not."""
    writer = CppBaseWrapperWriter({})
    args = [
        _arg("dim", default_value="DIM"),  # references the param -> substituted
        _arg("flag", default_value="true"),  # no param -> left as-is (else branch)
    ]
    result = writer.render_default_args(
        args,
        exclude_default_args=False,
        template_params=["DIM"],
        template_args=["2"],
        class_name="Foo",
    )
    assert result == ', py::arg("dim") = 2, py::arg("flag") = true'


def test_render_default_args_types_empty_initializer_list():
    """An empty {} default is given its type only when requested (constructors)."""
    from pygccxml import declarations

    writer = CppBaseWrapperWriter({})
    args = [_arg("v", default_value="{}", decl_type=declarations.int_t())]
    assert writer.render_default_args(
        args, exclude_default_args=False, substitute_empty_init_list=True
    ) == ', py::arg("v") = int {}'
