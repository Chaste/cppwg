"""Unit tests for cppwg.info.enum_info."""

import pytest

from cppwg.info.enum_info import CppEnumInfo


class _FakeLocation:
    def __init__(self, file_name, line=1):
        self.file_name = file_name
        self.line = line


class _FakeEnumDecl:
    """A minimal stand-in for a pygccxml enumeration_t."""

    def __init__(self, name, file_name, line=1):
        self.name = name
        self.location = _FakeLocation(file_name, line)


class _FakeNamespace:
    """A minimal stand-in for a pygccxml namespace."""

    def __init__(self, enums):
        self._enums = enums

    def enumerations(self, name, allow_empty=True):
        return self._enums


def test_enum_info_init_sets_name():
    """An enum info is created with its name and no config."""
    enum = CppEnumInfo("MyEnum")
    assert enum.name == "MyEnum"


def test_enum_info_init_applies_config():
    """Config values are applied through the base info initialiser."""
    enum = CppEnumInfo("MyEnum", {"excluded": True})
    assert enum.name == "MyEnum"
    assert enum.excluded is True


def test_update_from_ns_records_declaration_and_detects_scope(tmp_path):
    """The enum declaration is stored and its scopedness read from the source."""
    header = tmp_path / "Colors.hpp"
    header.write_text("enum class Scoped { A };\nenum Unscoped { B };\n")

    scoped = CppEnumInfo("Scoped")
    scoped.update_from_ns(
        _FakeNamespace([_FakeEnumDecl("Scoped", str(header), line=1)])
    )
    assert scoped.decls[0].name == "Scoped"
    assert scoped.scoped is True

    unscoped = CppEnumInfo("Unscoped")
    unscoped.update_from_ns(
        _FakeNamespace([_FakeEnumDecl("Unscoped", str(header), line=2)])
    )
    assert unscoped.scoped is False


def test_update_from_ns_raises_when_not_found():
    """An enum whose header was not parsed raises a clear error."""
    info = CppEnumInfo("Missing")

    with pytest.raises(RuntimeError, match="Could not find enum: Missing"):
        info.update_from_ns(_FakeNamespace([]))


def test_should_export_values_mirrors_scope_by_default():
    """With no override, export mirrors the C++ kind: unscoped yes, scoped no."""
    unscoped = CppEnumInfo("E")
    unscoped.scoped = False
    assert unscoped.should_export_values() is True

    scoped = CppEnumInfo("E")
    scoped.scoped = True
    assert scoped.should_export_values() is False


def test_should_export_values_override_wins():
    """An export_values override beats the C++ enum kind either way."""
    forced_off = CppEnumInfo("E")
    forced_off.scoped = False
    forced_off.export_values = False
    assert forced_off.should_export_values() is False

    forced_on = CppEnumInfo("E")
    forced_on.scoped = True
    forced_on.export_values = True
    assert forced_on.should_export_values() is True
