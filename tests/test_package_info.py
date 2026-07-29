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


def test_prune_keeps_excluded_class_without_instantiations():
    """An excluded class carries no cpp_names but must survive pruning.

    Excluded classes are never given cpp_names, so the no-instantiations drop
    would otherwise remove them - and log_unknown_classes would then report an
    explicitly excluded class as an unwrapped one. A non-excluded class with no
    instantiations is still dropped.
    """
    package, excluded = _package_with_class("StepSizeException")
    excluded.excluded = True

    module = package.module_collection[0]
    never_instantiated = CppClassInfo("NeverInstantiated")
    module.add_class(never_instantiated)

    package.prune_uninstantiated_dependencies(restricted_paths=[])

    names = [c.name for c in module.class_collection]
    assert "StepSizeException" in names
    assert "NeverInstantiated" not in names


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


def test_parse_typecaster_entry_strips_whitespace():
    """Surrounding whitespace on header and types is trimmed, not kept.

    A padded value like " Vec " must normalise to "Vec" (so it matches during
    scanning and the header emits a clean include), and a whitespace-only value
    must be treated as absent.
    """
    parse = PackageInfo.parse_typecaster_entry

    # Padded header and types are stripped.
    assert parse({"header": "  caster.h  ", "types": [" Vec ", "\tMat\n"]}) == (
        "caster.h",
        ["Vec", "Mat"],
    )

    # Types are normalized the same way matching is, so insignificant internal
    # whitespace is collapsed too (not just surrounding whitespace).
    assert parse({"header": "caster.h", "types": ["std::vector< double >"]}) == (
        "caster.h",
        ["std::vector<double>"],
    )

    # A whitespace-only header is malformed -> dropped.
    assert parse({"header": "   ", "types": ["Vec"]}) is None

    # Whitespace-only type entries are dropped; an entry left with none is dropped.
    assert parse({"header": "caster.h", "types": ["  ", "Mat"]}) == (
        "caster.h",
        ["Mat"],
    )
    assert parse({"header": "caster.h", "types": ["   "]}) is None


def test_parsed_typecasters_validated_once_and_cached(caplog):
    """Typecasters are parsed/validated once, warning once, and cached.

    Regression guard: the class writers check typecasters for every class, so a
    malformed entry must not warn once per class. Parsing happens once on
    PackageInfo and the result is cached.
    """
    import logging

    package_info = PackageInfo(
        "testpkg",
        {
            "source_root": "/tmp",
            "typecasters": [
                {"header": "caster.h", "types": ["Vec"]},
                "not-a-dict",  # malformed -> one warning, then dropped
            ],
        },
    )

    with caplog.at_level(logging.WARNING):
        first = package_info.parsed_typecasters
        second = package_info.parsed_typecasters  # would re-warn if not cached

    # Only the valid entry survives, as a (header, types) tuple.
    assert first == [("caster.h", ["Vec"])]
    # Cached: the same list object is returned, so no re-parse / re-warn.
    assert second is first
    warnings = [r for r in caplog.records if "typecasters" in r.getMessage()]
    assert len(warnings) == 1


def test_resolve_auto_includes_resolves_project_type_headers(tmp_path):
    """A project type used in a wrapped signature resolves to its header.

    The class's own header and library types are not added.
    """
    (tmp_path / "PottsMesh.hpp").write_text(
        "template<unsigned DIM> class PottsMesh {};\n"
    )
    (tmp_path / "MeshFactory.hpp").write_text(
        "template<class MESH> class MeshFactory {};\n"
    )

    package = PackageInfo("pkg", {"source_root": str(tmp_path)})
    package.source_hpp_files = [
        str(tmp_path / "PottsMesh.hpp"),
        str(tmp_path / "MeshFactory.hpp"),
    ]
    module = ModuleInfo("mod")
    package.add_module(module)

    cls = CppClassInfo("MeshFactory", {"auto_includes": True})
    cls.source_file = "MeshFactory.hpp"
    # generateMesh returns a PottsMesh (project type, resolved); a std return arg
    # is a library type (ignored); the copy-ctor arg names MeshFactory itself
    # (own header, dropped).
    method = _FakeCalldef(
        return_type="::std::shared_ptr<PottsMesh<2>>", name="generateMesh"
    )
    ctor = _FakeCalldef(
        argument_types=["::MeshFactory<PottsMesh<2>> const &"], name="MeshFactory"
    )
    cls.decls = [_FakeDecl(methods=[method], constructors=[ctor])]
    module.add_class(cls)

    package.resolve_auto_includes()

    assert cls.auto_include_headers == ["PottsMesh.hpp"]


def test_resolve_auto_includes_resolves_template_arg_headers(tmp_path):
    """Project types named as template arguments resolve to their headers.

    CellsGenerator<NoCellCycleModel, DIM> needs NoCellCycleModel.hpp even though
    the model type never appears in a wrapped signature. Numeric args (the
    dimension) resolve to nothing, and the class's own header is dropped.
    """
    (tmp_path / "CellsGenerator.hpp").write_text(
        "template<class MODEL, unsigned DIM> class CellsGenerator {};\n"
    )
    (tmp_path / "NoCellCycleModel.hpp").write_text("class NoCellCycleModel {};\n")
    (tmp_path / "UniformCellCycleModel.hpp").write_text(
        "class UniformCellCycleModel {};\n"
    )

    package = PackageInfo("pkg", {"source_root": str(tmp_path)})
    package.source_hpp_files = [
        str(tmp_path / "CellsGenerator.hpp"),
        str(tmp_path / "NoCellCycleModel.hpp"),
        str(tmp_path / "UniformCellCycleModel.hpp"),
    ]
    module = ModuleInfo("mod")
    package.add_module(module)

    cls = CppClassInfo("CellsGenerator", {"auto_includes": True})
    cls.source_file = "CellsGenerator.hpp"
    # The model types appear only as template arguments, never in a signature.
    cls.template_arg_lists = [
        ["NoCellCycleModel", "2"],
        ["UniformCellCycleModel", "3"],
    ]
    cls.decls = [_FakeDecl(), _FakeDecl()]
    module.add_class(cls)

    package.resolve_auto_includes()

    assert cls.auto_include_headers == [
        "NoCellCycleModel.hpp",
        "UniformCellCycleModel.hpp",
    ]


def test_resolve_auto_includes_noop_without_opt_in(tmp_path):
    """Without auto_includes enabled, no headers are resolved."""
    (tmp_path / "PottsMesh.hpp").write_text("class PottsMesh {};\n")

    package = PackageInfo("pkg", {"source_root": str(tmp_path)})
    package.source_hpp_files = [str(tmp_path / "PottsMesh.hpp")]
    module = ModuleInfo("mod")
    package.add_module(module)

    cls = CppClassInfo("MeshFactory")  # auto_includes not set
    cls.source_file = "MeshFactory.hpp"
    cls.decls = [_FakeDecl(methods=[_FakeCalldef(return_type="::PottsMesh<2>")])]
    module.add_class(cls)

    package.resolve_auto_includes()

    assert cls.auto_include_headers == []


def test_resolve_auto_includes_skipped_for_common_include_file(tmp_path):
    """auto_includes is a no-op when the common include file is used."""
    (tmp_path / "PottsMesh.hpp").write_text("class PottsMesh {};\n")

    package = PackageInfo(
        "pkg", {"source_root": str(tmp_path), "common_include_file": True}
    )
    package.source_hpp_files = [str(tmp_path / "PottsMesh.hpp")]
    module = ModuleInfo("mod")
    package.add_module(module)

    cls = CppClassInfo("MeshFactory", {"auto_includes": True})
    cls.source_file = "MeshFactory.hpp"
    cls.decls = [_FakeDecl(methods=[_FakeCalldef(return_type="::PottsMesh<2>")])]
    module.add_class(cls)

    package.resolve_auto_includes()

    assert cls.auto_include_headers == []


def test_build_type_header_map_drops_ambiguous_name(tmp_path):
    """A class name defined in two different headers is dropped (unresolvable)."""
    (tmp_path / "A.hpp").write_text("class Widget {};\nclass Alpha {};\n")
    (tmp_path / "B.hpp").write_text("class Widget {};\nclass Beta {};\n")

    package = PackageInfo("pkg", {"source_root": str(tmp_path)})
    package.source_hpp_files = [str(tmp_path / "A.hpp"), str(tmp_path / "B.hpp")]
    module = ModuleInfo("mod")
    package.add_module(module)

    mapping = package._build_type_header_map()

    assert mapping["Alpha"] == "A.hpp"
    assert mapping["Beta"] == "B.hpp"
    assert "Widget" not in mapping  # ambiguous -> dropped


from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402

import cppwg.info.package_info as package_info_module  # noqa: E402


def test_parse_exception_entry_bare_and_dict():
    assert PackageInfo.parse_exception_entry("MyError") == ("MyError", "what")
    assert PackageInfo.parse_exception_entry(
        {"name": "MyError", "message_method": "GetMessage"}
    ) == ("MyError", "GetMessage")
    assert PackageInfo.parse_exception_entry({"name": "MyError"}) == ("MyError", "what")


def test_exception_names_property():
    pkg = PackageInfo("pkg", {"source_root": "/src"})
    pkg.exceptions = ["A", {"name": "B", "message_method": "msg"}]
    assert pkg.exception_names == ["A", "B"]


@pytest.mark.parametrize(
    "entry, expected",
    [
        ({"header": "c.h", "types": "Vec"}, ("c.h", ["Vec"])),  # string -> [string]
        ({"header": "c.h", "types": 5}, None),  # non-list types -> dropped -> None
        ({"header": "c.h", "types": [5, "Mat"]}, ("c.h", ["Mat"])),  # non-str skipped
        ({"header": " c.h ", "types": [" Vec "]}, ("c.h", ["Vec"])),  # normalized
        ("not a dict", None),
        ({"types": ["Vec"]}, None),  # missing header
    ],
)
def test_parse_typecaster_entry(entry, expected):
    assert PackageInfo.parse_typecaster_entry(entry) == expected


class _ExcDecl:
    def __init__(self, name, methods, file_name="/src/Err.hpp"):
        self.name = name
        self._methods = methods
        self.recursive_bases = []
        self.location = SimpleNamespace(file_name=file_name)

    def member_functions(self, name, allow_empty=True):
        return [m for m in self._methods if m.name == name]


def _exc_ns(decls):
    return SimpleNamespace(
        classes=lambda pred, allow_empty=True: [d for d in decls if pred(d)]
    )


def test_resolve_exceptions_builds_translation_info(monkeypatch):
    """Each exception resolves to its message expression and header."""
    monkeypatch.setattr(
        package_info_module.declarations, "is_pointer", lambda rt: rt == "ptr"
    )
    what_method = SimpleNamespace(name="what", return_type="ptr")
    getmsg_method = SimpleNamespace(name="GetMessage", return_type="str")
    decls = [
        _ExcDecl("A", [what_method], "/src/A.hpp"),
        _ExcDecl("B", [getmsg_method], "/src/B.hpp"),
    ]

    pkg = PackageInfo("pkg", {"source_root": "/src"})
    pkg.exceptions = ["A", {"name": "B", "message_method": "GetMessage"}]
    pkg.resolve_exceptions(_exc_ns(decls))

    assert pkg.exception_info == [
        {"cpp_type": "A", "message_expr": "e.what()", "source_file": "A.hpp"},
        {
            "cpp_type": "B",
            "message_expr": "e.GetMessage().c_str()",
            "source_file": "B.hpp",
        },
    ]


def test_resolve_exceptions_missing_class_raises():
    pkg = PackageInfo("pkg", {"source_root": "/src"})
    pkg.exceptions = ["Missing"]
    with pytest.raises(RuntimeError, match="Could not find exception class: Missing"):
        pkg.resolve_exceptions(_exc_ns([]))


def test_resolve_exceptions_missing_method_raises():
    pkg = PackageInfo("pkg", {"source_root": "/src"})
    pkg.exceptions = [{"name": "A", "message_method": "GetMessage"}]
    decls = [_ExcDecl("A", [])]  # no GetMessage
    with pytest.raises(RuntimeError, match="has no method: GetMessage"):
        pkg.resolve_exceptions(_exc_ns(decls))


class _RaisingBasesDecl:
    """A decl whose recursive_bases access raises, as pygccxml can on odd types."""

    @property
    def recursive_bases(self):
        raise RuntimeError("pygccxml chokes on this decl")


class _BaseLink:
    def __init__(self, related_class):
        self.related_class = related_class


class _NamedDecl:
    def __init__(self, name, recursive_bases=(), bases=()):
        self.name = name
        self.recursive_bases = list(recursive_bases)
        self.bases = list(bases)


def test_discover_base_class_instantiations_harvests_and_skips():
    """Base-class instantiations are harvested; odd/irrelevant bases are skipped."""
    package = PackageInfo("pkg", {"source_root": "/src"})
    module = ModuleInfo("mod")
    package.add_module(module)

    # An opted-in, unresolved, templated target (1 template parameter).
    target = CppClassInfo("Base")
    target.discover_template_instantiations = True
    target._source_template_params = ["DIM"]
    module.add_class(target)

    # A wrapped class whose decls expose the target as a base at <2>.
    concrete = CppClassInfo("Concrete")
    normal = _NamedDecl(
        "Concrete",
        recursive_bases=[
            _BaseLink(None),  # unresolved base -> skipped
            _BaseLink(_NamedDecl("Other<2>")),  # not a target -> skipped
            _BaseLink(_NamedDecl("Base<2>")),  # harvested
            _BaseLink(_NamedDecl("Base<2>")),  # duplicate -> skipped
        ],
    )
    concrete.decls = [_RaisingBasesDecl(), normal]  # first decl raises -> skipped
    module.add_class(concrete)

    package.discover_base_class_instantiations(SimpleNamespace())

    # The single-arg harvested instantiation matches the 1-parameter target.
    assert target.template_arg_lists == [["2"]]
    assert target.cpp_names == ["Base<2>"]


def test_collect_source_files_skips_generated_and_restricted(tmp_path):
    """Generated .cppwg.hpp files and restricted paths are excluded."""
    (tmp_path / "Foo.hpp").write_text("")
    (tmp_path / "Bar.cppwg.hpp").write_text("")  # generated -> skipped
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "Vendored.hpp").write_text("")  # restricted -> skipped

    package = PackageInfo("pkg", {"source_root": str(tmp_path)})
    result = package.collect_source_files(["*.hpp"], [str(vendor)])

    assert [os.path.basename(p) for p in result] == ["Foo.hpp"]


def test_collect_source_headers_raises_when_none_found(tmp_path):
    """An empty source root with no headers is a fatal error."""
    package = PackageInfo("pkg", {"source_root": str(tmp_path)})
    with pytest.raises(FileNotFoundError):
        package.collect_source_headers([])


def test_referenced_instantiations_handles_unbalanced_and_nested():
    """Unbalanced brackets yield nothing; nested types yield each base/full pair."""
    referenced = package_info_module._referenced_instantiations
    assert list(referenced("Foo<2")) == []  # never-closed bracket -> skipped
    names = [base for base, _ in referenced("boost::shared_ptr<PottsMesh<2>>")]
    assert "shared_ptr" in names
    assert "PottsMesh" in names
