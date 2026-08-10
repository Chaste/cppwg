"""Unit tests for cppwg.writers.member_variable_writer."""

from types import SimpleNamespace

from pygccxml import declarations

from cppwg.templates.pybind11_default import template_collection
from cppwg.utils import utils
from cppwg.writers.member_variable_writer import CppClassMemberWrapperWriter


def _variable(name, decl_type=None, bits=None, static=False, parent=None):
    """Build a minimal pygccxml variable_t stand-in."""
    type_qualifiers = declarations.type_qualifiers_t()
    type_qualifiers.has_static = static
    return SimpleNamespace(
        name=name,
        decl_type=decl_type if decl_type is not None else declarations.double_t(),
        bits=bits,
        type_qualifiers=type_qualifiers,
        parent=parent,
    )


def _writer(variable, excluded_variables=()):
    """Wrap a fake variable in a writer with a minimal class info double."""
    class_decl = SimpleNamespace(name="Foo")
    # A direct member's parent is its owning class; only mark it nested if the
    # test supplied a different parent.
    if variable.parent is None:
        variable.parent = class_decl
    class_info = SimpleNamespace(
        decls=[class_decl],
        py_names=["Foo_2"],
        hierarchy_attribute_gather_flat=lambda key: (
            list(excluded_variables) if key == "excluded_variables" else []
        ),
    )
    return CppClassMemberWrapperWriter(class_info, 0, variable, template_collection)


def test_mutable_member_binds_readwrite():
    result = _writer(_variable("value")).generate_wrapper()
    assert result == '        .def_readwrite("value", &Foo_2::value)\n'


def test_const_member_binds_readonly():
    variable = _variable(
        "dimension", decl_type=declarations.const_t(declarations.int_t())
    )
    result = _writer(variable).generate_wrapper()
    assert result == '        .def_readonly("dimension", &Foo_2::dimension)\n'


def test_excluded_variable_is_skipped():
    writer = _writer(_variable("secret"), excluded_variables=["secret"])
    assert writer.exclude() is True
    assert writer.generate_wrapper() == ""


def test_bitfield_member_is_skipped():
    writer = _writer(_variable("packed", bits=3))
    assert writer.exclude() is True
    assert writer.generate_wrapper() == ""


def test_static_member_is_skipped():
    writer = _writer(_variable("shared", static=True))
    assert writer.exclude() is True
    assert writer.generate_wrapper() == ""


def test_array_member_is_skipped():
    # A C array member is not assignable, so def_readwrite would not compile.
    variable = _variable(
        "coords", decl_type=declarations.array_t(declarations.double_t(), 3)
    )
    writer = _writer(variable)
    assert writer.exclude() is True
    assert writer.generate_wrapper() == ""


def test_const_array_member_is_skipped():
    # A const array is not bindable read-only either (no caster for raw arrays).
    variable = _variable(
        "labels",
        decl_type=declarations.const_t(declarations.array_t(declarations.int_t(), 2)),
    )
    writer = _writer(variable)
    assert writer.exclude() is True
    assert writer.generate_wrapper() == ""


def test_reference_member_is_skipped():
    # A reference member cannot form a pointer-to-member, so &Foo::field is
    # ill-formed and it must not be bound.
    variable = _variable(
        "ref", decl_type=declarations.reference_t(declarations.double_t())
    )
    writer = _writer(variable)
    assert writer.exclude() is True
    assert writer.generate_wrapper() == ""


def test_nested_class_member_is_skipped():
    # The recursive variables() query also returns a nested class's fields; those
    # belong to a different parent and must not be bound as &Foo::field.
    nested_parent = SimpleNamespace(name="FooIterator")
    variable = _variable("index", parent=nested_parent)
    writer = _writer(variable)
    assert writer.exclude() is True
    assert writer.generate_wrapper() == ""


def test_non_copy_assignable_mutable_member_is_skipped(monkeypatch):
    # A mutable member whose type is not copy-assignable (e.g. std::unique_ptr)
    # cannot take the def_readwrite setter (obj.*pm = value), so it is skipped.
    monkeypatch.setattr(utils, "type_is_copy_assignable", lambda decl_type: False)
    writer = _writer(_variable("owned"))
    assert writer.exclude() is True
    assert writer.generate_wrapper() == ""


def test_non_copy_assignable_const_member_is_still_readonly(monkeypatch):
    # A const member is bound read-only (no setter), so copy-assignability is
    # irrelevant and it is not skipped.
    monkeypatch.setattr(utils, "type_is_copy_assignable", lambda decl_type: False)
    variable = _variable("frozen", decl_type=declarations.const_t(declarations.int_t()))
    writer = _writer(variable)
    assert writer.exclude() is False
    assert (
        writer.generate_wrapper() == '        .def_readonly("frozen", &Foo_2::frozen)\n'
    )


def test_class_py_name_falls_back_to_decl_name():
    """With no python name set, the binding refers to the class by its decl name."""
    class_decl = SimpleNamespace(name="Bar")
    class_info = SimpleNamespace(
        decls=[class_decl],
        py_names=[None],
        hierarchy_attribute_gather_flat=lambda key: [],
    )
    writer = CppClassMemberWrapperWriter(
        class_info, 0, _variable("x", parent=class_decl), template_collection
    )
    assert writer.generate_wrapper() == '        .def_readwrite("x", &Bar::x)\n'
