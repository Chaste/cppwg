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
    """An opted-in class with no args and unknown templated-ness needs discovery.

    With no resolved header path the class is treated conservatively as possibly
    templated, so discovery still runs.
    """
    package, cls = _package_with_class()
    cls.discover_template_instantiations = True

    assert package.uses_template_discovery() is True


def test_uses_template_discovery_false_for_untemplated_class(tmp_path):
    """An opted-in class known to be untemplated does not trigger discovery."""
    header = tmp_path / "Foo.hpp"
    header.write_text("class Foo {};\n")

    package, cls = _package_with_class("Foo")
    cls.discover_template_instantiations = True
    cls.source_file_path = str(header)

    assert package.uses_template_discovery() is False


def test_uses_template_discovery_true_for_templated_class(tmp_path):
    """An opted-in templated class (per its header) triggers discovery."""
    header = tmp_path / "Foo.hpp"
    header.write_text("template <unsigned DIM> class Foo {};\n")

    package, cls = _package_with_class("Foo")
    cls.discover_template_instantiations = True
    cls.source_file_path = str(header)

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


class _FakeType:
    """A stand-in for a pygccxml type, exposing only its decl_string."""

    def __init__(self, decl_string):
        self.decl_string = decl_string


class _FakeCalldef:
    """A stand-in for a member function / constructor decl."""

    def __init__(self, argument_types=(), return_type=None, name="method"):
        self.name = name
        self.argument_types = [_FakeType(t) for t in argument_types]
        self.return_type = _FakeType(return_type) if return_type else None


class _FakeDecl:
    """A stand-in for a class decl, exposing the parts the prune consults."""

    def __init__(self, methods=(), constructors=(), is_abstract=False):
        self._methods = list(methods)
        self._constructors = list(constructors)
        self.is_abstract = is_abstract
        self.recursive_bases = []
        self.bases = []

    def member_functions(self, function=None, allow_empty=False):
        return self._methods

    def constructors(self, function=None, allow_empty=False):
        return self._constructors


def _py_name(cpp_name):
    """Turn a cpp instantiation name into a python name e.g. Foo<2, 2> -> Foo_2_2."""
    return (
        cpp_name.replace("<", "_")
        .replace(">", "")
        .replace(",", "_")
        .replace(" ", "")
    )


def _wrap(cls, cpp_names, decls):
    """Attach wrapped instantiations (cpp/py names + decls) to a class info."""
    cls.cpp_names = list(cpp_names)
    cls.py_names = [_py_name(name) for name in cpp_names]
    cls.decls = list(decls)


def test_prune_drops_instantiation_with_uninstantiated_dependency():
    """A wrapped instantiation exposing an uninstantiated project type is dropped."""
    package, cls = _package_with_class("Facet")
    _wrap(
        cls,
        ["Facet<1>", "Facet<2>"],
        [
            _FakeDecl(methods=[_FakeCalldef(return_type="Facet<0> *")]),
            _FakeDecl(methods=[_FakeCalldef(return_type="Facet<1> *")]),
        ],
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    # Facet<1> -> Facet<0> (never instantiated) is dropped; Facet<2> -> Facet<1>
    # (a wrapped instantiation) survives.
    assert cls.cpp_names == ["Facet<2>"]
    assert cls.py_names == ["Facet_2"]


def test_prune_ignores_dependency_reached_only_through_excluded_method():
    """A dependency reached only via an excluded method does not trigger a drop."""
    package, cls = _package_with_class("VertexMesh")
    cls.excluded_methods = ["GetFace"]
    _wrap(
        cls,
        ["VertexMesh<1, 2>", "VertexMesh<2, 2>"],
        [
            _FakeDecl(
                methods=[
                    _FakeCalldef(return_type="VertexMesh<0, 2> *", name="GetFace")
                ]
            ),
            _FakeDecl(methods=[]),
        ],
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    # "VertexMesh" is a project base (VertexMesh<1,2>/<2,2> are wrapped), and
    # VertexMesh<0,2> is uninstantiated - but GetFace, which returns it, is
    # excluded, so VertexMesh<1, 2> is not pruned.
    assert cls.cpp_names == ["VertexMesh<1, 2>", "VertexMesh<2, 2>"]


def test_prune_ignores_library_types():
    """A dependency not sharing a base name with a wrapped class is left alone."""
    package, cls = _package_with_class("Node")
    _wrap(
        cls,
        ["Node<2>"],
        [_FakeDecl(methods=[_FakeCalldef(return_type="std::vector<double>")])],
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    assert cls.cpp_names == ["Node<2>"]


def test_prune_keeps_sibling_when_dependency_is_source_instantiated(tmp_path):
    """A dependency instantiated only in source (not wrapped) is not pruned."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "Facet.cpp").write_text("template class Facet<1>;\n")

    package = PackageInfo("pkg", {"source_root": str(src)})
    module = ModuleInfo("mod")
    cls = CppClassInfo("Facet")
    package.add_module(module)
    module.add_class(cls)

    # Only Facet<2> is wrapped (as if Facet<1> were curated out), but Facet<1> is
    # explicitly instantiated in Facet.cpp above.
    _wrap(cls, ["Facet<2>"], [_FakeDecl(methods=[_FakeCalldef(return_type="Facet<1> *")])])

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    assert cls.cpp_names == ["Facet<2>"]


def test_prune_drops_sibling_when_dependency_not_instantiated_anywhere():
    """Control: a dependency neither wrapped nor instantiated in source is pruned."""
    package, cls = _package_with_class("Facet")
    _wrap(cls, ["Facet<2>"], [_FakeDecl(methods=[_FakeCalldef(return_type="Facet<1> *")])])

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    assert cls.cpp_names == []


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
