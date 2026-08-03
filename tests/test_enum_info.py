"""Unit tests for cppwg.info.enum_info."""

from cppwg.info.enum_info import CppEnumInfo


def test_enum_info_init_sets_name():
    """An enum info is created with its name and no config."""
    enum = CppEnumInfo("MyEnum")
    assert enum.name == "MyEnum"


def test_enum_info_init_applies_config():
    """Config values are applied through the base info initialiser."""
    enum = CppEnumInfo("MyEnum", {"excluded": True})
    assert enum.name == "MyEnum"
    assert enum.excluded is True
