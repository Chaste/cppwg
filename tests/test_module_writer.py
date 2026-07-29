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


import pytest  # noqa: E402

from cppwg.templates.pybind11_default import template_collection  # noqa: E402
from cppwg.writers import module_writer as module_writer_module  # noqa: E402


class _ClassStub:
    def __init__(self, name, stem, excluded=False):
        self.name = name
        self.excluded = excluded
        self._stem = stem
        self.decls = []
        self.cpp_names = []

    def py_name_base(self):
        return self._stem


class _FakeClassWriter:
    def __init__(self, *args):
        pass

    def write(self, work_dir):
        pass


def test_write_class_wrappers_rejects_duplicate_file_stem(tmp_path, monkeypatch):
    """Two classes mapping to the same wrapper file name fail fast."""
    monkeypatch.setattr(
        module_writer_module, "CppClassWrapperWriter", _FakeClassWriter
    )
    module = _module(
        classes=[_ClassStub("Foo", "Widget"), _ClassStub("Bar", "Widget")]
    )
    writer = CppModuleWrapperWriter(module, template_collection, str(tmp_path))

    with pytest.raises(ValueError, match="used by both"):
        writer.write_class_wrappers()


def test_write_module_wrapper_creates_module_dir(tmp_path, monkeypatch):
    """The module's output directory is created when it does not exist."""
    from string import Template

    module = _module(name="mymod")
    module.package_info.name = "pkg"  # for full_module_name
    writer = CppModuleWrapperWriter(
        module, {"module_main_cpp": Template("body")}, str(tmp_path)
    )
    monkeypatch.setattr(writer, "build_module_context", dict)

    writer.write_module_wrapper()

    assert (tmp_path / "mymod").is_dir()
