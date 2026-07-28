"""Unit tests for cppwg.writers.module_writer."""

from types import SimpleNamespace

from cppwg.writers.module_writer import CppModuleWrapperWriter


def _module(classes=None, exception_info=None, name="mod"):
    """Build a minimal module info (and back-referencing package) stand-in."""
    package = SimpleNamespace(exception_info=list(exception_info or []))
    module = SimpleNamespace(
        class_collection=list(classes or []), package_info=package, name=name
    )
    package.module_collection = [module]
    return module


def test_generate_exception_translator_empty_without_exceptions(tmp_path):
    """With no configured exceptions, the translator code is empty."""
    writer = CppModuleWrapperWriter(_module(), {}, str(tmp_path))
    assert writer.generate_exception_translator() == ""


def test_init_skips_excluded_classes(tmp_path):
    """Excluded classes are not collected into the module's decl map."""
    excluded = SimpleNamespace(name="Hidden", excluded=True, decls=[], cpp_names=[])
    included = SimpleNamespace(
        name="Foo", excluded=False, decls=["foo_decl"], cpp_names=["Foo"]
    )
    writer = CppModuleWrapperWriter(
        _module(classes=[excluded, included]), {}, str(tmp_path)
    )
    assert writer.classes == {"foo_decl": "Foo"}
