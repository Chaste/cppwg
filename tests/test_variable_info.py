"""Unit tests for cppwg.info.variable_info."""

from cppwg.info.variable_info import CppVariableInfo


def test_variable_info_init_sets_name():
    """A variable info is created with its name and no config."""
    var = CppVariableInfo("my_var")
    assert var.name == "my_var"


def test_variable_info_init_applies_config():
    """Config values are applied through the base info initialiser."""
    var = CppVariableInfo("my_var", {"excluded": True})
    assert var.name == "my_var"
    assert var.excluded is True
