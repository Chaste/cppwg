"""Unit tests for cppwg.info.class_info."""

from cppwg.info.class_info import CppClassInfo
from cppwg.info.module_info import ModuleInfo
from cppwg.info.package_info import PackageInfo


def test_apply_template_instantiations_populates_names_when_enabled():
    """Discovered instantiations set template args and rebuild class names."""
    cls = CppClassInfo("Foo")
    cls.discover_template_instantiations = True
    cls.update_names()  # untemplated names, as produced by update_from_source

    cls.apply_template_instantiations({"Foo": [["2"], ["3"]]})

    assert cls.template_arg_lists == [["2"], ["3"]]
    assert cls.cpp_names == ["Foo<2>", "Foo<3>"]
    assert cls.py_names == ["Foo_2", "Foo_3"]


def test_apply_template_instantiations_recovers_template_params(tmp_path):
    """Discovery recovers template parameter names from the class header.

    These drive default-argument substitution (e.g. `= SPACE_DIM` -> `= 2`),
    which the instantiated decls cannot supply.
    """
    source = tmp_path / "AbstractMesh.hpp"
    source.write_text(
        "template <unsigned ELEMENT_DIM, unsigned SPACE_DIM = ELEMENT_DIM>\n"
        "class AbstractMesh {};\n"
    )

    cls = CppClassInfo("AbstractMesh")
    cls.discover_template_instantiations = True
    cls.source_file_path = str(source)
    cls.update_names()

    cls.apply_template_instantiations({"AbstractMesh": [["2", "2"], ["3", "3"]]})

    assert cls.template_params == ["ELEMENT_DIM", "SPACE_DIM"]
    assert cls.cpp_names == ["AbstractMesh<2, 2>", "AbstractMesh<3, 3>"]


def test_apply_template_instantiations_is_noop_when_disabled():
    """With discovery off (the default), the map is ignored."""
    cls = CppClassInfo("Foo")
    cls.update_names()

    cls.apply_template_instantiations({"Foo": [["2"], ["3"]]})

    assert cls.template_arg_lists == []
    assert cls.cpp_names == ["Foo"]


def test_template_substitutions_take_precedence_over_discovery():
    """A class with template args already set is left untouched by discovery."""
    cls = CppClassInfo("Foo")
    cls.discover_template_instantiations = True
    cls.template_arg_lists = [[2, 2]]  # e.g. from template_substitutions
    cls.update_names()

    cls.apply_template_instantiations({"Foo": [["2"], ["3"]]})

    assert cls.template_arg_lists == [[2, 2]]
    assert cls.cpp_names == ["Foo<2, 2>"]


def test_apply_template_instantiations_skips_class_absent_from_map():
    """A class with no discovered instantiations stays untemplated."""
    cls = CppClassInfo("Foo")
    cls.discover_template_instantiations = True
    cls.update_names()

    cls.apply_template_instantiations({"Bar": [["2"]]})

    assert cls.template_arg_lists == []
    assert cls.cpp_names == ["Foo"]


def test_discovery_flag_inherited_from_package():
    """A package-level discovery flag enables discovery for its classes.

    The flag defaults to None (inherit); hierarchy_attribute ascends the info
    tree, so setting it once on the package applies to every class.
    """
    package = PackageInfo("pkg", {"source_root": "/src"})
    package.discover_template_instantiations = True
    module = ModuleInfo("mod")
    cls = CppClassInfo("Foo")
    package.add_module(module)
    module.add_class(cls)
    cls.update_names()

    cls.apply_template_instantiations({"Foo": [["2"]]})

    assert cls.cpp_names == ["Foo<2>"]


def test_extract_templates_skips_non_dict_substitution(tmp_path):
    """A mis-typed template_substitutions entry is skipped, not crashed on.

    Each substitution must be a dict with a signature/replacement; a yaml scalar
    (e.g. `template_substitutions: 5`) would otherwise raise on `entry["..."]`.
    """
    source = tmp_path / "Foo.hpp"
    source.write_text("class Foo {};\n")

    cls = CppClassInfo("Foo")
    cls.source_file_path = str(source)
    cls.template_substitutions = [5, "foo"]  # mis-typed scalar entries

    cls.extract_templates_from_source()  # must not raise

    assert cls.template_arg_lists == []
    assert cls.template_params == []


def _discovery_class(name, params, excludes=None):
    """A class info with fixed template params and optional discover_arg_excludes."""
    cls = CppClassInfo(name)
    cls._source_template_params = params  # bypass reading the header source
    if excludes is not None:
        cls.discover_arg_excludes = excludes
    return cls


def test_filter_discovered_instantiations_excludes_named_dim():
    """A dimension parameter's excluded values drop those instantiations."""
    cls = _discovery_class("ChastePoint", ["DIM"], {"DIM": [0, 1]})
    assert cls.filter_discovered_instantiations([["0"], ["1"], ["2"], ["3"]]) == [
        ["2"],
        ["3"],
    ]


def test_filter_discovered_instantiations_matches_by_parameter_name():
    """Only the named parameter is matched, not any argument of that value.

    For <SPACE_DIM, PROBLEM_DIM>, SPACE_DIM=1 is excluded but a PROBLEM_DIM of 1
    is kept - so Foo<2, 1> survives while Foo<1, 1> and Foo<1, 2> are dropped.
    """
    cls = _discovery_class("Foo", ["SPACE_DIM", "PROBLEM_DIM"], {"SPACE_DIM": [1]})
    result = cls.filter_discovered_instantiations(
        [["1", "1"], ["2", "1"], ["1", "2"], ["2", "2"]]
    )
    assert result == [["2", "1"], ["2", "2"]]


def test_filter_discovered_instantiations_keeps_trailing_non_spatial_one():
    """A trailing non-spatial 1 (e.g. PROBLEM_DIM) is kept: Bar<2, 2, 1> survives."""
    cls = _discovery_class(
        "Bar",
        ["ELEMENT_DIM", "SPACE_DIM", "PROBLEM_DIM"],
        {"ELEMENT_DIM": [1], "SPACE_DIM": [1]},
    )
    result = cls.filter_discovered_instantiations(
        [["1", "1", "1"], ["2", "2", "1"], ["1", "2", "1"]]
    )
    assert result == [["2", "2", "1"]]


def test_filter_discovered_instantiations_no_excludes_is_noop():
    """With no discover_arg_excludes set, all instantiations are kept."""
    cls = _discovery_class("Foo", ["DIM"])
    assert cls.filter_discovered_instantiations([["1"], ["2"]]) == [["1"], ["2"]]


def test_filter_discovered_instantiations_unknown_params_is_noop():
    """When parameter names cannot be recovered, nothing is filtered."""
    cls = _discovery_class("Foo", [], {"DIM": [1]})
    assert cls.filter_discovered_instantiations([["1"], ["2"]]) == [["1"], ["2"]]


def test_filter_discovered_instantiations_accepts_typed_param_key():
    """A key may carry a leading type ('unsigned ELEMENT_DIM'), as signatures do."""
    cls = _discovery_class(
        "Bar",
        ["ELEMENT_DIM", "SPACE_DIM"],
        {"unsigned ELEMENT_DIM": [1], "unsigned SPACE_DIM": [1]},
    )
    result = cls.filter_discovered_instantiations(
        [["1", "1"], ["1", "2"], ["2", "2"], ["2", "3"]]
    )
    assert result == [["2", "2"], ["2", "3"]]


from types import SimpleNamespace  # noqa: E402

from pygccxml.declarations.runtime_errors import declaration_not_found_t  # noqa: E402


class _FakeArg:
    def __init__(self, decl_string):
        self.decl_string = decl_string


class _FakeCalldef:
    def __init__(self, arg_strings):
        self.argument_types = [_FakeArg(s) for s in arg_strings]


class _FakeClassDecl:
    def __init__(self, name="Foo", methods=(), ctors=(), bases=(), file_name="/s/Foo.hpp"):
        self.name = name
        self._methods = list(methods)
        self._ctors = list(ctors)
        self.bases = list(bases)
        self.location = SimpleNamespace(file_name=file_name)

    def member_functions(self, function=None, allow_empty=True):
        return self._methods

    def constructors(self, function=None, allow_empty=True):
        return self._ctors


class _FakeNs:
    def __init__(self, classes=None, typedefs=None):
        self._classes = classes or {}
        self._typedefs = typedefs or {}

    def class_(self, name):
        if name in self._classes:
            return self._classes[name]
        raise declaration_not_found_t("no class " + name)

    def typedef(self, name):
        if name in self._typedefs:
            return self._typedefs[name]
        raise declaration_not_found_t("no typedef " + name)


def test_signature_arg_types_collects_method_and_ctor_args():
    cls = CppClassInfo("Foo")
    cls.decls = [
        _FakeClassDecl(
            methods=[_FakeCalldef(["Bar<2> const &"])],
            ctors=[_FakeCalldef(["double"])],
        )
    ]
    assert cls.signature_arg_types() == ["Bar<2> const &", "double"]


def test_requires_detects_used_type():
    cls = CppClassInfo("Foo")
    cls.decls = [_FakeClassDecl(methods=[_FakeCalldef(["Bar<2> const &"])])]
    assert cls.requires(CppClassInfo("Bar")) is True
    assert cls.requires(CppClassInfo("Baz")) is False


def test_update_from_source_matches_by_class_name(tmp_path):
    src = tmp_path / "Foo.hpp"
    src.write_text("class Foo {};\n")
    cls = CppClassInfo("Foo")
    cls.update_from_source([str(src)])
    assert cls.source_file == "Foo.hpp"
    assert cls.source_file_path == str(src)
    assert cls.cpp_names == ["Foo"]
    assert cls.py_names == ["Foo"]


def test_update_from_source_with_existing_source_file_path(tmp_path):
    src = tmp_path / "dir" / "Foo.hpp"
    src.parent.mkdir()
    src.write_text("class Foo {};\n")
    cls = CppClassInfo("Foo")
    cls.source_file_path = str(src)
    cls.update_from_source([])
    assert cls.source_file == "Foo.hpp"


def test_update_from_source_skips_excluded():
    cls = CppClassInfo("Foo", {"excluded": True})
    cls.update_from_source(["/s/Foo.hpp"])
    assert cls.cpp_names == []


def test_update_from_ns_resolves_class_and_bases():
    foo_decl = _FakeClassDecl(name="Foo", bases=[SimpleNamespace(related_class="BaseObj")])
    ns = _FakeNs(classes={"Foo": foo_decl})
    cls = CppClassInfo("Foo")
    cls.cpp_names = ["Foo"]
    cls.py_names = ["Foo"]
    cls.update_from_ns(ns)
    assert cls.decls == [foo_decl]
    assert cls.source_file == "Foo.hpp"
    assert cls.base_decls == ["BaseObj"]


def test_update_from_ns_resolves_via_typedef():
    real_decl = _FakeClassDecl(name="Foo<2>")
    typedef_decl = SimpleNamespace(
        decl_type=SimpleNamespace(declaration=real_decl)
    )
    ns = _FakeNs(typedefs={"Foo_2": typedef_decl})
    cls = CppClassInfo("Foo")
    cls.cpp_names = ["Foo<2>"]
    cls.py_names = ["Foo_2"]
    cls.update_from_ns(ns)
    assert cls.decls == [real_decl]
    assert real_decl.name == "Foo<2>"


def test_update_from_ns_defers_unresolved_instantiation():
    cls = CppClassInfo("Foo")
    cls.cpp_names = ["Foo<9>"]
    cls.py_names = ["Foo_9"]
    cls.update_from_ns(_FakeNs())
    assert cls.decls == []
    assert cls.cpp_names == []


def test_update_from_ns_skips_excluded():
    cls = CppClassInfo("Foo", {"excluded": True})
    cls.cpp_names = ["Foo"]
    cls.py_names = ["Foo"]
    cls.update_from_ns(_FakeNs())
    assert cls.decls == []


def test_update_names_untemplated():
    cls = CppClassInfo("Foo")
    cls.update_names()
    assert cls.cpp_names == ["Foo"]
    assert cls.py_names == ["Foo"]


def test_update_names_templated():
    cls = CppClassInfo("Foo")
    cls.template_arg_lists = [[2, 2], [3, 3]]
    cls.update_names()
    assert cls.cpp_names == ["Foo<2, 2>", "Foo<3, 3>"]
    assert cls.py_names == ["Foo_2_2", "Foo_3_3"]


def test_update_py_names_capitalizes_multichar_arg():
    """A multi-character template argument has its first letter capitalized."""
    cls = CppClassInfo("MeshFactory")
    cls.template_arg_lists = [["pottsMesh", 2]]
    cls.update_py_names()
    assert cls.py_names == ["MeshFactory_PottsMesh_2"]


def test_py_name_base_single_char_templated():
    """A one-character templated base is returned without capitalization work."""
    cls = CppClassInfo("F")
    cls.template_arg_lists = [[2]]
    assert cls.py_name_base() == "F"


def test_update_from_ns_keeps_template_arg_lists():
    """A resolved templated instantiation keeps its parallel template_arg_lists."""
    decl = _FakeClassDecl(name="Foo<2>")
    ns = _FakeNs(classes={"Foo<2>": decl})
    cls = CppClassInfo("Foo")
    cls.cpp_names = ["Foo<2>"]
    cls.py_names = ["Foo_2"]
    cls.template_arg_lists = [["2"]]
    cls.update_from_ns(ns)
    assert cls.cpp_names == ["Foo<2>"]
    assert cls.template_arg_lists == [["2"]]


def test_update_from_source_matches_by_source_file(tmp_path):
    """A class whose source_file is set matches the file with that basename."""
    src = tmp_path / "Custom.hpp"
    src.write_text("class Foo {};\n")
    cls = CppClassInfo("Foo")
    cls.source_file = "Custom.hpp"
    cls.update_from_source([str(src)])
    assert cls.source_file_path == str(src)


def test_template_has_defaulted_params_without_source():
    """With no source file, a class is treated as having no defaulted params."""
    assert CppClassInfo("Foo").template_has_defaulted_params() is False


def test_template_has_defaulted_params_reads_source(tmp_path):
    """A defaulted template parameter is detected from the class header."""
    src = tmp_path / "Foo.hpp"
    src.write_text("template<unsigned A, unsigned B = A> class Foo {};\n")
    cls = CppClassInfo("Foo")
    cls.source_file_path = str(src)
    assert cls.template_has_defaulted_params() is True


def test_extract_templates_skips_when_args_already_set():
    """extract_templates_from_source does nothing if template args are set."""
    cls = CppClassInfo("Foo")
    cls.template_arg_lists = [["2"]]
    cls.extract_templates_from_source()
    assert cls.template_arg_lists == [["2"]]


def test_extract_templates_skips_without_source_file():
    """extract_templates_from_source does nothing without a source file."""
    cls = CppClassInfo("Foo")
    cls.extract_templates_from_source()
    assert cls.template_arg_lists == []


def test_apply_template_instantiations_skips_excluded_class():
    """An excluded class adopts no discovered instantiations."""
    cls = CppClassInfo("Foo", {"excluded": True})
    cls.apply_template_instantiations({"Foo": [["2"]]})
    assert cls.cpp_names == []


def test_apply_template_instantiations_no_match_for_class():
    """A class absent from the instantiation map is left untemplated."""
    cls = CppClassInfo("Foo")
    cls.discover_template_instantiations = True
    cls.apply_template_instantiations({"Other": [["2"]]})
    assert cls.template_arg_lists == []
