"""Unit tests for cppwg.writers.free_function_writer exclusion behaviour."""

from cppwg.writers.free_function_writer import CppFreeFunctionWrapperWriter


class _Type:
    """Stand-in for a pygccxml type (only decl_string is used)."""

    def __init__(self, decl_string):
        self.decl_string = decl_string


class _Decl:
    """Minimal free_function_t stand-in."""

    def __init__(self, return_type, arg_types):
        self.return_type = _Type(return_type)
        self.argument_types = [_Type(a) for a in arg_types]


class _FreeFunctionInfo:
    """Minimal CppFreeFunctionInfo stand-in for exclusion lookups."""

    def __init__(self, return_type, arg_types, excludes=None):
        self.decls = [_Decl(return_type, arg_types)]
        self._excludes = excludes or {}

    def hierarchy_attribute_gather_flat(self, name):
        return list(self._excludes.get(name, []))


def _writer(return_type="void", arg_types=(), excludes=None):
    info = _FreeFunctionInfo(return_type, list(arg_types), excludes)
    writer = object.__new__(CppFreeFunctionWrapperWriter)
    writer.free_function_info = info
    return writer


def test_free_function_arg_type_exclude_respects_boundaries():
    """arg_type_excludes drops free functions by argument type, as a whole token."""
    excludes = {"arg_type_excludes": ["Node"]}

    assert _writer(arg_types=["::Node<2> const &"], excludes=excludes).exclude() is True
    assert (
        _writer(arg_types=["::AbstractNode<2> const &"], excludes=excludes).exclude()
        is False
    )


def test_free_function_return_type_exclude():
    """return_type_excludes drops free functions by return type only."""
    excludes = {"return_type_excludes": ["RawPtr"]}

    assert _writer(return_type="::RawPtr *", excludes=excludes).exclude() is True
    assert _writer(return_type="int", excludes=excludes).exclude() is False
    assert _writer(arg_types=["::RawPtr *"], excludes=excludes).exclude() is False


def test_free_function_calldef_exclude_applies_to_both():
    """The deprecated calldef_excludes matches both return and argument types."""
    excludes = {"calldef_excludes": ["Foo"]}

    assert _writer(return_type="::Foo &", excludes=excludes).exclude() is True
    assert _writer(arg_types=["::Foo const &"], excludes=excludes).exclude() is True


def test_free_function_not_excluded_without_options():
    """With no exclusion options set, nothing is excluded."""
    assert _writer(return_type="int", arg_types=["double"]).exclude() is False
