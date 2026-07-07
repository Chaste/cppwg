"""Unit tests for cppwg.writers.constructor_writer exclusion behaviour."""

from cppwg.info.base_info import BaseInfo
from cppwg.writers import constructor_writer as constructor_writer_module
from cppwg.writers.constructor_writer import CppConstructorWrapperWriter


class _Type:
    """Stand-in for a pygccxml type (only decl_string is used)."""

    def __init__(self, decl_string):
        self.decl_string = decl_string


class _ClassDecl:
    """Minimal class_t stand-in for the early checks in exclude()."""

    is_abstract = False
    recursive_bases = []

    def member_functions(self, allow_empty=True):
        return []


class _CtorDecl:
    """Minimal constructor_t stand-in."""

    is_artificial = False

    def __init__(self, arg_types, parent):
        self.argument_types = [_Type(a) for a in arg_types]
        self.parent = parent


class _ClassInfo:
    """Minimal CppClassInfo stand-in that mirrors production gathering."""

    def __init__(self, signature_excludes=None):
        self._signature_excludes = signature_excludes

    def hierarchy_attribute_gather(self, name):
        if name == "constructor_signature_excludes" and self._signature_excludes:
            return [self._signature_excludes]
        return []

    # Borrow production so the double cannot diverge (scalar handling etc.).
    hierarchy_attribute_gather_flat = BaseInfo.hierarchy_attribute_gather_flat


def _writer(arg_types, signature_excludes, monkeypatch):
    # is_copy_constructor inspects a real pygccxml decl; stub it out so exclude()
    # reaches the signature-exclude loop with our lightweight fakes.
    monkeypatch.setattr(
        constructor_writer_module.type_traits_classes,
        "is_copy_constructor",
        lambda decl: False,
    )
    class_decl = _ClassDecl()
    writer = object.__new__(CppConstructorWrapperWriter)
    writer.class_info = _ClassInfo(signature_excludes)
    writer.class_decl = class_decl
    writer.ctor_decl = _CtorDecl(arg_types, parent=class_decl)
    return writer


def test_signature_exclude_matches_valid_signature(monkeypatch):
    """A well-formed nested signature excludes a matching constructor."""
    writer = _writer(["int", "int", "int"], [["int", "int", "int"]], monkeypatch)
    assert writer.exclude() is True


def test_signature_exclude_skips_scalar_int(monkeypatch):
    """A mis-typed scalar (constructor_signature_excludes: 5) is skipped, not len()'d."""
    writer = _writer(["int", "int", "int"], 5, monkeypatch)
    assert writer.exclude() is False


def test_signature_exclude_skips_scalar_string(monkeypatch):
    """A mis-typed scalar string is skipped, not iterated character by character."""
    writer = _writer(["int", "int", "int"], "int", monkeypatch)
    assert writer.exclude() is False
