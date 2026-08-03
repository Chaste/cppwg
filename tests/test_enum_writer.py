"""Unit tests for cppwg.writers.enum_writer."""

from cppwg.templates.pybind11_default import template_collection
from cppwg.writers.enum_writer import CppEnumWrapperWriter


class _FakeEnum:
    """Minimal pygccxml enumeration_t stand-in.

    ``values`` is a list of (name, number) tuples, as pygccxml exposes them.
    """

    def __init__(self, name, values):
        self.name = name
        self.values = values


class _FakeEnumInfo:
    """Minimal CppEnumInfo stand-in."""

    def __init__(self, name, values, name_override="", excluded=False):
        self.name = name
        self.name_override = name_override
        self.excluded = excluded
        self.decls = [_FakeEnum(name, values)]


def _writer(info):
    return CppEnumWrapperWriter(info, template_collection)


def test_generate_wrapper_emits_enum_registration():
    """Each enumerator becomes a .value line qualified by the enum type."""
    info = _FakeEnumInfo("Color", [("RED", 0), ("GREEN", 1), ("BLUE", 2)])

    result = _writer(info).generate_wrapper()

    assert result == (
        '    py::enum_<Color>(m, "Color")\n'
        '    .value("RED", Color::RED)\n'
        '    .value("GREEN", Color::GREEN)\n'
        '    .value("BLUE", Color::BLUE)\n'
        "    .export_values();\n\n"
    )


def test_generate_wrapper_uses_name_override_for_python_name():
    """The Python name comes from name_override; values stay C++-qualified."""
    info = _FakeEnumInfo("CppColor", [("RED", 0)], name_override="Color")

    result = _writer(info).generate_wrapper()

    assert result == (
        '    py::enum_<CppColor>(m, "Color")\n'
        '    .value("RED", CppColor::RED)\n'
        "    .export_values();\n\n"
    )


def test_generate_wrapper_excluded_returns_empty():
    """An excluded enum generates no wrapper code."""
    info = _FakeEnumInfo("Color", [("RED", 0)], excluded=True)

    assert _writer(info).generate_wrapper() == ""
