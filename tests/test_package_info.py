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


def test_collect_source_files_orders_same_basename_deterministically(tmp_path):
    """Files sharing a basename are ordered by full path, not os.walk order."""
    src = tmp_path / "src"
    (src / "b").mkdir(parents=True)
    (src / "a").mkdir(parents=True)
    (src / "b" / "Foo.cpp").write_text("")
    (src / "a" / "Foo.cpp").write_text("")
    (src / "Bar.cpp").write_text("")

    package_info = PackageInfo("testpkg", {"source_root": str(src)})
    package_info.collect_source_cpp(restricted_paths=[])

    # Sorted by basename first (Bar before Foo), then full path (a before b) as a
    # deterministic tie-break for the two Foo.cpp files.
    assert package_info.source_cpp_files == [
        str(src / "Bar.cpp"),
        str(src / "a" / "Foo.cpp"),
        str(src / "b" / "Foo.cpp"),
    ]


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


def _base_discovery_package(tmp_path, base_class_name="AbstractLinearPde"):
    """Package with an opted-in 2-param abstract base and a wrapped derived class.

    Returns (package, base_class_info, base_decl) where a concrete wrapped class
    derives (recursively) from base_decl.
    """
    header = tmp_path / f"{base_class_name}.hpp"
    header.write_text(
        f"template<unsigned A, unsigned B> class {base_class_name} {{}};\n"
    )

    package = PackageInfo("pkg", {"source_root": str(tmp_path)})
    module = ModuleInfo("mod")
    package.add_module(module)

    base = CppClassInfo(base_class_name)
    base.discover_template_instantiations = True
    base.source_file_path = str(header)
    module.add_class(base)

    return package, module, base


def test_discover_base_class_instantiations_from_hierarchy(tmp_path):
    """An abstract base is discovered from a wrapped class's base hierarchy."""
    package, module, base = _base_discovery_package(tmp_path)

    base_decl = _FakeDecl(name="AbstractLinearPde<2, 2>")
    concrete = CppClassInfo("CellwiseSourcePde")
    concrete.cpp_names = ["CellwiseSourcePde<2>"]
    concrete.py_names = ["CellwiseSourcePde_2"]
    concrete.decls = [_FakeDecl(recursive_bases=[_FakeBase(base_decl)])]
    module.add_class(concrete)

    package.discover_base_class_instantiations(source_ns=None)

    assert base.template_arg_lists == [["2", "2"]]
    assert base.cpp_names == ["AbstractLinearPde<2, 2>"]
    assert base.decls == [base_decl]


def test_discover_base_class_instantiations_rejects_collapsed_arg(tmp_path):
    """A base whose defaulted arg CastXML collapsed (too few args) is not adopted."""
    package, module, base = _base_discovery_package(tmp_path)

    # CastXML collapsed the defaulted second arg, naming the base "…<2>".
    base_decl = _FakeDecl(name="AbstractLinearPde<2>")
    concrete = CppClassInfo("CellwiseSourcePde")
    concrete.cpp_names = ["CellwiseSourcePde<2>"]
    concrete.py_names = ["CellwiseSourcePde_2"]
    concrete.decls = [_FakeDecl(recursive_bases=[_FakeBase(base_decl)])]
    module.add_class(concrete)

    package.discover_base_class_instantiations(source_ns=None)

    # Two params expected but only one arg -> rejected, left for substitutions.
    assert base.template_arg_lists == []


def test_update_template_instantiations_merges_fallback_into_discovered():
    """A merging pass adds new (e.g. macro) instantiations to discovered args."""
    package, cls = _package_with_class()
    cls.discover_template_instantiations = True

    package.update_template_instantiations({"Foo": [["1"]]})  # text scan
    assert cls.cpp_names == ["Foo<1>"]
    assert cls.template_args_from_discovery is True

    # Fallback finds an additional macro instantiation Foo<2>.
    package.update_template_instantiations({"Foo": [["1"], ["2"]]}, merge=True)
    assert cls.cpp_names == ["Foo<1>", "Foo<2>"]


def test_update_template_instantiations_merge_does_not_extend_substitutions():
    """A merging pass never extends args that came from template_substitutions."""
    package, cls = _package_with_class()
    cls.discover_template_instantiations = True
    cls.template_arg_lists = [["2"]]  # as if set by template_substitutions

    package.update_template_instantiations({"Foo": [["2"], ["3"]]}, merge=True)

    assert cls.template_arg_lists == [["2"]]


def test_update_template_instantiations_merge_skips_defaulted_when_untrusted(tmp_path):
    """A defaulted-param class is not merged when CastXML drops defaulted args."""
    header = tmp_path / "Mesh.hpp"
    header.write_text("template<unsigned A, unsigned B = A> class Mesh {};\n")

    package, cls = _package_with_class("Mesh")
    cls.discover_template_instantiations = True
    cls.source_file_path = str(header)
    package.update_template_instantiations({"Mesh": [["2", "2"]]})  # text scan

    # An untrusted CastXML would offer "Mesh<2>" for the same instantiation; the
    # merge is skipped to avoid a differently-rendered duplicate.
    package.update_template_instantiations(
        {"Mesh": [["2"]]}, merge=True, trust_defaulted_args=False
    )
    assert cls.template_arg_lists == [["2", "2"]]


def test_update_template_instantiations_merge_defaulted_when_trusted(tmp_path):
    """A defaulted-param class merges when CastXML preserves defaulted args."""
    header = tmp_path / "Mesh.hpp"
    header.write_text("template<unsigned A, unsigned B = A> class Mesh {};\n")

    package, cls = _package_with_class("Mesh")
    cls.discover_template_instantiations = True
    cls.source_file_path = str(header)
    package.update_template_instantiations({"Mesh": [["2", "2"]]})

    package.update_template_instantiations(
        {"Mesh": [["2", "2"], ["3", "3"]]}, merge=True, trust_defaulted_args=True
    )
    assert cls.template_arg_lists == [["2", "2"], ["3", "3"]]


def test_update_template_instantiations_merge_non_defaulted_when_untrusted(tmp_path):
    """A class with no defaulted params merges even with an untrusted CastXML."""
    header = tmp_path / "Foo.hpp"
    header.write_text("template<unsigned DIM> class Foo {};\n")

    package, cls = _package_with_class("Foo")
    cls.discover_template_instantiations = True
    cls.source_file_path = str(header)
    package.update_template_instantiations({"Foo": [["1"]]})

    package.update_template_instantiations(
        {"Foo": [["1"], ["2"]]}, merge=True, trust_defaulted_args=False
    )
    assert cls.template_arg_lists == [["1"], ["2"]]


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


class _FakeBase:
    """A stand-in for a pygccxml hierarchy_info_t (a base class entry)."""

    def __init__(self, related_class):
        self.related_class = related_class


class _FakeDecl:
    """A stand-in for a class decl, exposing the parts the prune consults."""

    def __init__(
        self,
        methods=(),
        constructors=(),
        is_abstract=False,
        name=None,
        recursive_bases=(),
    ):
        self._methods = list(methods)
        self._constructors = list(constructors)
        self.is_abstract = is_abstract
        self.name = name
        self.recursive_bases = list(recursive_bases)
        self.bases = []

    def member_functions(self, function=None, allow_empty=False):
        return self._methods

    def constructors(self, function=None, allow_empty=False):
        return self._constructors


def _py_name(cpp_name):
    """Turn a cpp instantiation name into a python name e.g. Foo<2, 2> -> Foo_2_2."""
    return (
        cpp_name.replace("<", "_").replace(">", "").replace(",", "_").replace(" ", "")
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
                methods=[_FakeCalldef(return_type="VertexMesh<0, 2> *", name="GetFace")]
            ),
            _FakeDecl(methods=[]),
        ],
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    # "VertexMesh" is a project base (VertexMesh<1,2>/<2,2> are wrapped), and
    # VertexMesh<0,2> is uninstantiated - but GetFace, which returns it, is
    # excluded, so VertexMesh<1, 2> is not pruned.
    assert cls.cpp_names == ["VertexMesh<1, 2>", "VertexMesh<2, 2>"]


def test_prune_flags_uninstantiated_enclosing_template():
    """An uninstantiated enclosing template is flagged, not just its arguments."""
    package, cls = _package_with_class("Widget")
    _wrap(
        cls,
        ["Widget<Gadget<2>>", "Widget<Gadget<3>>"],
        [
            _FakeDecl(methods=[]),
            _FakeDecl(
                methods=[_FakeCalldef(return_type="Widget<Gadget<0>> *", name="Get")]
            ),
        ],
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    # The enclosing Widget<Gadget<0>> is uninstantiated, so Widget<Gadget<3>> is
    # dropped - a match that is missed if only the innermost Gadget<0> is checked
    # (Gadget is not a project base).
    assert cls.cpp_names == ["Widget<Gadget<2>>"]


def test_prune_ignores_dependency_in_signature_excluded_constructor():
    """A dependency reached only via a signature-excluded constructor is ignored."""
    package, cls = _package_with_class("Widget")
    cls.constructor_signature_excludes = [["Widget<0> *"]]
    _wrap(
        cls,
        ["Widget<1>", "Widget<2>"],
        [
            _FakeDecl(constructors=[_FakeCalldef(argument_types=["Widget<0> *"])]),
            _FakeDecl(),
        ],
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    # The only reference to the uninstantiated Widget<0> is in a constructor
    # whose full signature is excluded, so Widget<1> is not pruned.
    assert cls.cpp_names == ["Widget<1>", "Widget<2>"]


def test_prune_treats_macro_instantiation_as_instantiated():
    """A macro-only instantiation is counted as instantiated during pruning.

    The source-text scan cannot see macro-generated instantiations, so a type
    instantiated only via a macro (even one curated out of wrapping) would look
    uninstantiated and wrongly prune a wrapped dependent. Discovery records such
    instantiations in macro_instantiations, which pruning must honour.
    """
    package, foo = _package_with_class("Foo")
    _wrap(foo, ["Foo<2>"], [_FakeDecl()])  # makes "Foo" a known project template
    bar = CppClassInfo("Bar")
    package.module_collection[0].add_class(bar)
    _wrap(bar, ["Bar<1>"], [_FakeDecl(methods=[_FakeCalldef(return_type="Foo<0> *")])])

    # Foo<0> is explicitly instantiated via a macro (and curated out of wrapping).
    package.macro_instantiations = {"Foo<0>"}

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    # Bar<1> survives because its dependency Foo<0> is instantiated by the macro.
    assert bar.cpp_names == ["Bar<1>"]


def test_prune_drops_dependent_on_unrecorded_macro_instantiation():
    """Without the macro instantiation recorded, the dependent is pruned.

    Documents the behaviour that test_prune_treats_macro_instantiation_as_-
    instantiated guards against: an unknown Foo<0> looks uninstantiated.
    """
    package, foo = _package_with_class("Foo")
    _wrap(foo, ["Foo<2>"], [_FakeDecl()])
    bar = CppClassInfo("Bar")
    package.module_collection[0].add_class(bar)
    _wrap(bar, ["Bar<1>"], [_FakeDecl(methods=[_FakeCalldef(return_type="Foo<0> *")])])

    # macro_instantiations is left empty (the default), so Foo<0> is unknown.
    package.prune_uninstantiated_dependencies(restricted_paths=[])

    assert bar.cpp_names == []


def test_prune_matches_namespaced_dependency_against_unqualified_instantiation():
    """A namespace-qualified dependency matches its unqualified instantiation.

    A pygccxml decl_string keeps namespace qualifiers (e.g. "ns::Foo<0>") while
    cpp_names are unqualified ("Foo<0>"). Pruning compares them in the same
    unqualified form, else a wrapped instantiation of a namespaced type would
    look uninstantiated and its dependents be wrongly dropped.
    """
    package, foo = _package_with_class("Foo")
    _wrap(foo, ["Foo<0>", "Foo<2>"], [_FakeDecl(), _FakeDecl()])
    bar = CppClassInfo("Bar")
    package.module_collection[0].add_class(bar)
    _wrap(
        bar, ["Bar<1>"], [_FakeDecl(methods=[_FakeCalldef(return_type="ns::Foo<0> *")])]
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    # ns::Foo<0> resolves to the wrapped Foo<0>, so Bar<1> survives.
    assert bar.cpp_names == ["Bar<1>"]


def test_prune_drops_namespaced_dependency_when_uninstantiated():
    """A namespaced dependency with no matching instantiation is still pruned."""
    package, foo = _package_with_class("Foo")
    _wrap(foo, ["Foo<2>"], [_FakeDecl()])
    bar = CppClassInfo("Bar")
    package.module_collection[0].add_class(bar)
    _wrap(
        bar, ["Bar<1>"], [_FakeDecl(methods=[_FakeCalldef(return_type="ns::Foo<0> *")])]
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    # ns::Foo<0> reduces to Foo<0>, which is not instantiated, so Bar<1> is dropped.
    assert bar.cpp_names == []


def test_prune_keeps_template_arg_lists_aligned():
    """Pruning an instantiation removes its template_arg_lists entry too.

    The writers index template_arg_lists by position (e.g. to substitute template
    params in default arguments), so a dropped instantiation must not leave the
    list misaligned with cpp_names.
    """
    package, cls = _package_with_class("Foo")
    _wrap(
        cls,
        ["Foo<1>", "Foo<2>", "Foo<3>"],
        [
            _FakeDecl(methods=[_FakeCalldef(return_type="Foo<0> *")]),  # dropped
            _FakeDecl(),
            _FakeDecl(),
        ],
    )
    cls.template_arg_lists = [["1"], ["2"], ["3"]]

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    assert cls.cpp_names == ["Foo<2>", "Foo<3>"]
    assert cls.template_arg_lists == [["2"], ["3"]]


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
    _wrap(
        cls, ["Facet<2>"], [_FakeDecl(methods=[_FakeCalldef(return_type="Facet<1> *")])]
    )

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    assert cls.cpp_names == ["Facet<2>"]


def test_prune_drops_sibling_when_dependency_not_instantiated_anywhere():
    """Control: a dependency neither wrapped nor instantiated in source is pruned."""
    package, cls = _package_with_class("Facet")
    _wrap(
        cls, ["Facet<2>"], [_FakeDecl(methods=[_FakeCalldef(return_type="Facet<1> *")])]
    )

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
