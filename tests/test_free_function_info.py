"""Unit tests for cppwg.info.free_function_info."""

import pytest

from cppwg.info.free_function_info import CppFreeFunctionInfo


class _FakeNamespace:
    """A minimal stand-in for a pygccxml namespace."""

    def __init__(self, free_functions):
        self._free_functions = free_functions

    def free_functions(self, name, allow_empty=True):
        return self._free_functions


def test_update_from_ns_records_first_declaration():
    """The first matching free-function declaration is stored."""
    info = CppFreeFunctionInfo("my_func")
    ns = _FakeNamespace(["decl0", "decl1"])

    info.update_from_ns(ns)

    assert info.decls == ["decl0"]


def test_update_from_ns_raises_when_not_found():
    """A free function whose header was not parsed raises a clear error."""
    info = CppFreeFunctionInfo("missing_func")
    ns = _FakeNamespace([])

    with pytest.raises(RuntimeError, match="Could not find free function: missing_func"):
        info.update_from_ns(ns)
