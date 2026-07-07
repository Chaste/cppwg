"""Unit tests for cppwg.info.package_info."""

import os

from cppwg.info.class_info import CppClassInfo
from cppwg.info.module_info import ModuleInfo
from cppwg.info.package_info import PackageInfo


def test_collect_source_cpp_collects_implementation_files(tmp_path):
    """Implementation files matching source_cpp_patterns are collected."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "Foo.cpp").write_text("")
    (src / "Foo.hpp").write_text("")

    package_info = PackageInfo("testpkg", {"source_root": str(src)})
    package_info.collect_source_cpp(restricted_paths=[])

    basenames = {os.path.basename(f) for f in package_info.source_cpp_files}
    assert basenames == {"Foo.cpp"}


def _package_with_class(class_name="Foo"):
    """Build a package -> module -> class tree and return (package, class)."""
    package = PackageInfo("pkg", {"source_root": "/src"})
    module = ModuleInfo("mod")
    cls = CppClassInfo(class_name)
    package.add_module(module)
    module.add_class(cls)
    return package, cls


def test_uses_template_discovery_true_when_class_opted_in():
    """Discovery is needed when an opted-in class has no template args yet."""
    package, cls = _package_with_class()
    cls.discover_template_instantiations = True

    assert package.uses_template_discovery() is True


def test_uses_template_discovery_false_by_default():
    """With no class opted in, discovery is skipped."""
    package, _ = _package_with_class()

    assert package.uses_template_discovery() is False


def test_uses_template_discovery_false_when_args_already_set():
    """An opted-in class that already has template args does not need discovery."""
    package, cls = _package_with_class()
    cls.discover_template_instantiations = True
    cls.template_arg_lists = [[2, 2]]

    assert package.uses_template_discovery() is False


def test_update_template_instantiations_distributes_map_to_classes():
    """The instantiation map is applied to each opted-in class."""
    package, cls = _package_with_class()
    cls.discover_template_instantiations = True

    package.update_template_instantiations({"Foo": [["2"], ["3"]]})

    assert cls.cpp_names == ["Foo<2>", "Foo<3>"]


def test_collect_source_headers_skips_restricted_paths(tmp_path):
    """Headers under a restricted path are excluded from the source collection.

    Regression test: the restricted-path skip previously used a `continue`
    inside the restricted_paths loop, which only advanced that loop instead of
    skipping the file, so a header under a restricted path (e.g. the wrapper
    output directory nested in the source root) was collected anyway.
    """
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    wrapper = src / "wrapper"
    wrapper.mkdir()

    (src / "Keep.hpp").write_text("")
    # A plain header inside the restricted path. It is not a .cppwg.hpp file, so
    # only the restricted-path check can exclude it.
    (wrapper / "Skip.hpp").write_text("")

    package_info = PackageInfo("testpkg", {"source_root": str(src)})
    package_info.collect_source_headers(restricted_paths=[str(wrapper)])

    basenames = {os.path.basename(f) for f in package_info.source_hpp_files}
    assert "Keep.hpp" in basenames
    assert "Skip.hpp" not in basenames
