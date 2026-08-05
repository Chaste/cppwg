"""Unit tests for cppwg.writers.member_variable_writer."""

from types import SimpleNamespace

from pygccxml import declarations

from cppwg.templates.pybind11_default import template_collection
from cppwg.writers.member_variable_writer import CppClassMemberWrapperWriter


def _variable(name, decl_type=None, bits=None, static=False):
    """Build a minimal pygccxml variable_t stand-in."""
    type_qualifiers = declarations.type_qualifiers_t()
    type_qualifiers.has_static = static
    return SimpleNamespace(
        name=name,
        decl_type=decl_type if decl_type is not None else declarations.double_t(),
        bits=bits,
        type_qualifiers=type_qualifiers,
    )


def _writer(variable, excluded_variables=()):
    """Wrap a fake variable in a writer with a minimal class info double."""
    class_decl = SimpleNamespace(name="Foo")
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


def test_class_py_name_falls_back_to_decl_name():
    """With no python name set, the binding refers to the class by its decl name."""
    class_decl = SimpleNamespace(name="Bar")
    class_info = SimpleNamespace(
        decls=[class_decl],
        py_names=[None],
        hierarchy_attribute_gather_flat=lambda key: [],
    )
    writer = CppClassMemberWrapperWriter(
        class_info, 0, _variable("x"), template_collection
    )
    assert writer.generate_wrapper() == '        .def_readwrite("x", &Bar::x)\n'
