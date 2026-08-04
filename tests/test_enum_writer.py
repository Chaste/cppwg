"""Unit tests for cppwg.writers.enum_writer."""

from cppwg.info.enum_info import CppEnumInfo
from cppwg.templates.pybind11_default import template_collection
from cppwg.writers.enum_writer import CppEnumWrapperWriter


class _FakeEnum:
    """Minimal pygccxml enumeration_t stand-in.

    ``values`` is a list of (name, number) tuples, as pygccxml exposes them.
    """

    def __init__(self, name, values):
        self.name = name
        self.values = values


def _FakeEnumInfo(
    name, values, name_override="", excluded=False, scoped=False, export_values=None
):
    """Build a real CppEnumInfo with a faked pygccxml decl.

    Using the real info object exercises the actual should_export_values /
    hierarchy_attribute logic; only the pygccxml enumeration_t is faked.
    """
    info = CppEnumInfo(name)
    info.name_override = name_override
    info.excluded = excluded
    info.scoped = scoped
    info.export_values = export_values
    info.decls = [_FakeEnum(name, values)]
    return info


def _writer(info):
    return CppEnumWrapperWriter(info, template_collection)


def test_generate_wrapper_emits_enum_registration():
    """An unscoped enum registers each value and exports them with .export_values()."""
    info = _FakeEnumInfo("Color", [("RED", 0), ("GREEN", 1), ("BLUE", 2)])

    result = _writer(info).generate_wrapper()

    assert result == (
        '    py::enum_<Color>(m, "Color")\n'
        '    .value("RED", Color::RED)\n'
        '    .value("GREEN", Color::GREEN)\n'
        '    .value("BLUE", Color::BLUE)\n'
        "    .export_values();\n\n"
    )


def test_generate_wrapper_scoped_enum_omits_export_values():
    """A scoped enum does not export its enumerators into the enclosing scope."""
    info = _FakeEnumInfo("Color", [("RED", 0), ("GREEN", 1)], scoped=True)

    result = _writer(info).generate_wrapper()

    assert result == (
        '    py::enum_<Color>(m, "Color")\n'
        '    .value("RED", Color::RED)\n'
        '    .value("GREEN", Color::GREEN)\n'
        "    ;\n\n"
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


def test_export_values_override_suppresses_export_on_unscoped_enum():
    """export_values=False omits export even for an unscoped enum."""
    info = _FakeEnumInfo("Color", [("RED", 0)], export_values=False)

    result = _writer(info).generate_wrapper()

    assert "    .export_values();\n" not in result
    assert result.endswith('    .value("RED", Color::RED)\n    ;\n\n')


def test_export_values_override_forces_export_on_scoped_enum():
    """export_values=True emits export even for a scoped enum."""
    info = _FakeEnumInfo("Color", [("RED", 0)], scoped=True, export_values=True)

    result = _writer(info).generate_wrapper()

    assert result.endswith('    .value("RED", Color::RED)\n    .export_values();\n\n')


def test_generate_wrapper_excluded_returns_empty():
    """An excluded enum generates no wrapper code."""
    info = _FakeEnumInfo("Color", [("RED", 0)], excluded=True)

    assert _writer(info).generate_wrapper() == ""
