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
