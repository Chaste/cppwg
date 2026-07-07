"""Unit tests for cppwg.writers.method_writer exclusion behaviour."""

from cppwg.writers.method_writer import CppMethodWrapperWriter


class _Type:
    """Stand-in for a pygccxml type (only decl_string is used)."""

    def __init__(self, decl_string):
        self.decl_string = decl_string


class _Method:
    """Minimal member_function_t stand-in."""

    def __init__(self, name, return_type, arg_types, parent, access="public"):
        self.name = name
        self.return_type = _Type(return_type)
        self.argument_types = [_Type(a) for a in arg_types]
        self.access_type = access
        self.parent = parent


class _ClassInfo:
    """Minimal CppClassInfo stand-in for exclusion lookups."""

    def __init__(self, excludes=None, excluded_methods=None):
        self._excludes = excludes or {}
        self.excluded_methods = excluded_methods or []

    def hierarchy_attribute_gather_flat(self, name):
        return list(self._excludes.get(name, []))


def _writer(class_info, return_type="void", arg_types=(), access="public"):
    class_decl = object()
    method = _Method("Foo", return_type, list(arg_types), class_decl, access)
    writer = object.__new__(CppMethodWrapperWriter)
    writer.class_info = class_info
    writer.method_decl = method
    writer.class_decl = class_decl
    return writer


def test_arg_type_exclude_respects_identifier_boundaries():
    """A method taking the excluded arg type is dropped; a look-alike is kept."""
    class_info = _ClassInfo(excludes={"arg_type_excludes": ["Node"]})

    assert _writer(class_info, arg_types=["::Node<2> const &"]).exclude() is True
    assert _writer(class_info, arg_types=["::AbstractNode<2> const &"]).exclude() is False
    assert _writer(class_info, arg_types=["int"]).exclude() is False


def test_return_type_exclude():
    """return_type_excludes drops methods by return type only."""
    class_info = _ClassInfo(excludes={"return_type_excludes": ["RawPtr"]})

    assert _writer(class_info, return_type="::RawPtr *").exclude() is True
    assert _writer(class_info, return_type="int").exclude() is False
    # A return-type pattern does not exclude on arguments.
    assert _writer(class_info, arg_types=["::RawPtr *"]).exclude() is False


def test_calldef_exclude_applies_to_both_return_and_args():
    """The deprecated calldef_excludes matches both return and argument types."""
    class_info = _ClassInfo(excludes={"calldef_excludes": ["Foo"]})

    assert _writer(class_info, return_type="::Foo &").exclude() is True
    assert _writer(class_info, arg_types=["::Foo const &"]).exclude() is True
    assert _writer(class_info, return_type="int", arg_types=["double"]).exclude() is False
