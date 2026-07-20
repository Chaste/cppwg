"""Unit tests for cppwg.writers.class_writer."""

from cppwg.info.base_info import BaseInfo
from cppwg.templates.pybind11_default import template_collection
from cppwg.writers.class_writer import CppClassWrapperWriter


class _FakeLocation:
    """Stand-in for a pygccxml declaration location."""

    def __init__(self, file_name):
        self.file_name = file_name


class _FakeEnum:
    """Stand-in for a pygccxml enumeration_t."""

    def __init__(self, name, values):
        self.name = name
        self.values = values  # list of (name, value) tuples


class _FakeStructDecl:
    """Stand-in for a pygccxml class_t describing a struct with one enum."""

    def __init__(self, name, file_name, enum):
        self.name = name
        self.location = _FakeLocation(file_name)
        self._enum = enum

    def enumerations(self, allow_empty=False):
        return [self._enum]


class _FakeClassInfo:
    """Minimal CppClassInfo stand-in for exercising the writer directly."""

    def __init__(
        self,
        name,
        decl,
        attrs,
        source_file,
        cpp_names=None,
        py_names=None,
        name_base=None,
        decls=None,
        generator=None,
    ):
        self.name = name
        self.cpp_names = cpp_names if cpp_names is not None else [name]
        self.py_names = py_names if py_names is not None else [name]
        self.decls = decls if decls is not None else [decl]
        self.source_file = source_file
        self.prefix_code = []
        self.suffix_code = []
        self.custom_generator_instance = generator
        self._name_base = name_base or name
        self._attrs = attrs

    def py_name_base(self):
        return self._name_base

    def hierarchy_attribute(self, key):
        return self._attrs.get(key)

    def hierarchy_attribute_gather(self, key):
        value = self._attrs.get(key)
        return [value] if value else []

    # Borrow the production flatten so this double cannot diverge from BaseInfo
    # (e.g. its scalar handling); it only depends on hierarchy_attribute_gather.
    hierarchy_attribute_gather_flat = BaseInfo.hierarchy_attribute_gather_flat


def _make_writer(class_info):
    """Build a class writer around a fake class info object."""
    return CppClassWrapperWriter(class_info, template_collection, module_classes={})


def test_struct_enum_wrapper_common_include():
    """A struct wrapping a single enum registers the enum values.

    Regression test for the struct-enum special case, which no example in the
    repo exercises. Pins the generated output for the common-include-file path
    with a smart pointer holder.
    """
    enum = _FakeEnum("Value", [("RED", 0), ("GREEN", 1), ("BLUE", 2)])
    decl = _FakeStructDecl("Color", "/src/Color.hpp", enum)
    class_info = _FakeClassInfo(
        "Color",
        decl,
        attrs={"common_include_file": True, "smart_ptr_type": "std::shared_ptr"},
        source_file="Color.hpp",
    )

    writer = _make_writer(class_info)
    header = writer.build_cpp_header("typedef Color Color;\n")
    block = writer.build_struct_enum_register(0)

    # The shared preamble carries the includes, the holder (exactly once) and the
    # instantiation's alias typedef.
    assert '#include "wrapper_header_collection.cppwg.hpp"\n' in header
    assert header.count("PYBIND11_DECLARE_HOLDER_TYPE(T, std::shared_ptr<T>);") == 1
    assert "typedef Color Color;\n" in header

    # The per-instantiation registration block wraps the enum values; the alias
    # typedef lives in the preamble, not the block. It opens with the (empty)
    # generator pre-code slot followed by a blank line, mirroring the normal
    # class_cpp_register block.
    expected_block = (
        "\n"
        "void register_Color_class(py::module &m){\n"
        '    py::class_<Color> myclass(m, "Color");\n'
        '    py::enum_<Color::Value>(myclass, "Value")\n'
        '        .value("RED", Color::Value::RED)\n'
        '        .value("GREEN", Color::Value::GREEN)\n'
        '        .value("BLUE", Color::Value::BLUE)\n'
        "    .export_values();\n"
        "}\n"
    )
    assert block == expected_block


def test_struct_enum_wrapper_uses_wrapper_alias_not_cpp_decl_name():
    """The registration refers to the class by its wrapper alias, not decl name.

    Regression test: when the Python wrapper name differs from the C++ decl name
    (name overrides, templated instantiations), the registration function must
    be named after the wrapper alias so it matches the hpp declaration and the
    module's register_..._class call. Using the C++ decl name would define a
    different symbol and fail to link/import.
    """
    enum = _FakeEnum("Value", [("RED", 0), ("GREEN", 1)])
    # C++ decl name "Color", but wrapped in Python as "MyColor".
    decl = _FakeStructDecl("Color", "/src/Color.hpp", enum)
    class_info = _FakeClassInfo(
        "Color",
        decl,
        attrs={"common_include_file": True, "smart_ptr_type": "std::shared_ptr"},
        source_file="Color.hpp",
        cpp_names=["Color"],
        py_names=["MyColor"],
        name_base="MyColor",
    )

    writer = _make_writer(class_info)
    header = writer.build_cpp_header("typedef Color MyColor;\n")
    block = writer.build_struct_enum_register(0)

    # The wrapper file and its include are named after the Python alias, and the
    # preamble defines the alias (C++ decl "Color" -> Python "MyColor").
    assert '#include "MyColor.cppwg.hpp"\n' in header
    assert "typedef Color MyColor;\n" in header

    # The registration refers to the class by the alias throughout, opening with
    # the (empty) generator pre-code slot and a blank line.
    expected_block = (
        "\n"
        "void register_MyColor_class(py::module &m){\n"
        '    py::class_<MyColor> myclass(m, "MyColor");\n'
        '    py::enum_<MyColor::Value>(myclass, "Value")\n'
        '        .value("RED", MyColor::Value::RED)\n'
        '        .value("GREEN", MyColor::Value::GREEN)\n'
        "    .export_values();\n"
        "}\n"
    )
    assert block == expected_block

    # The cpp definition and the hpp declaration must be for the same symbol.
    assert "void register_MyColor_class(" in block
    assert "void register_MyColor_class(" in writer.build_hpp(["MyColor"])


def test_struct_enum_wrapper_source_includes_and_prefix():
    """The struct-enum path honours prefix text and explicit source includes.

    Covers the non-common-include-file branch (explicit source includes plus the
    class source file) and the empty smart-pointer handle.
    """
    enum = _FakeEnum("Value", [("RED", 0)])
    decl = _FakeStructDecl("Color", "/src/Color.hpp", enum)
    class_info = _FakeClassInfo(
        "Color",
        decl,
        attrs={
            "common_include_file": False,
            "source_includes": ["<memory>"],
            "prefix_text": "// auto",
        },
        source_file="Color.hpp",
    )

    header = _make_writer(class_info).build_cpp_header("")

    # Non-common-include-file path: prefix text, then the explicit source
    # includes and the class source file; the empty holder renders as ";".
    expected_header = (
        "// auto\n"
        "#include <pybind11/pybind11.h>\n"
        "#include <pybind11/stl.h>\n"
        "#include <memory>\n"
        '#include "Color.hpp"\n'
        "\n"
        '#include "Color.cppwg.hpp"\n'
        "\n"
        "namespace py = pybind11;\n"
        ";\n"
    )
    assert header == expected_header


def test_combined_wrapper_shares_one_preamble_for_all_instantiations():
    """All instantiations of a class share one file: one preamble, N register fns.

    Pins issue #30 Phase 1 - the includes, namespace and holder appear once, the
    hpp declares a register function for every instantiation, and each
    instantiation contributes its own alias typedef and register function.
    """
    enum2 = _FakeEnum("Value", [("A", 0)])
    enum3 = _FakeEnum("Value", [("A", 0)])
    decl2 = _FakeStructDecl("Foo", "/src/Foo.hpp", enum2)
    decl3 = _FakeStructDecl("Foo", "/src/Foo.hpp", enum3)
    class_info = _FakeClassInfo(
        "Foo",
        decl2,
        attrs={"common_include_file": True, "smart_ptr_type": "std::shared_ptr"},
        source_file="Foo.hpp",
        cpp_names=["Foo<2>", "Foo<3>"],
        py_names=["Foo_2", "Foo_3"],
        name_base="Foo",
        decls=[decl2, decl3],
    )
    writer = _make_writer(class_info)

    # The single hpp declares a register function for every instantiation.
    hpp = writer.build_hpp(["Foo_2", "Foo_3"])
    assert "void register_Foo_2_class(" in hpp
    assert "void register_Foo_3_class(" in hpp
    assert hpp.count("#define Foo_hpp__cppwg_wrapper") == 1

    # The combined cpp is one shared preamble (carrying every instantiation's
    # alias typedef) + one register block per instantiation. This mirrors how
    # write() assembles the preamble from the gathered alias typedefs.
    class_typedefs = "typedef Foo<2> Foo_2;\ntypedef Foo<3> Foo_3;\n"
    cpp = (
        writer.build_cpp_header(class_typedefs)
        + "\n"
        + "\n".join(writer.build_struct_enum_register(i) for i in range(2))
    )
    assert cpp.count("namespace py = pybind11;") == 1
    assert cpp.count("PYBIND11_DECLARE_HOLDER_TYPE") == 1
    assert cpp.count('#include "Foo.cppwg.hpp"') == 1
    assert "typedef Foo<2> Foo_2;" in cpp
    assert "typedef Foo<3> Foo_3;" in cpp
    assert "void register_Foo_2_class(" in cpp
    assert "void register_Foo_3_class(" in cpp

    # Every alias typedef precedes all registration code, so any block can refer
    # to any instantiation by its alias.
    last_typedef = max(
        cpp.index("typedef Foo<2> Foo_2;"), cpp.index("typedef Foo<3> Foo_3;")
    )
    first_register = min(
        cpp.index("void register_Foo_2_class("),
        cpp.index("void register_Foo_3_class("),
    )
    assert last_typedef < first_register


class _FakeGenerator:
    """Custom generator whose pre-code refers to the class by its wrapper alias.

    Mirrors real generators (e.g. CellsGenerator's) that emit an override class
    inheriting the alias in their pre-code.
    """

    def get_class_cpp_pre_code(self, class_py_name):
        return f"class {class_py_name}_Overrides : public {class_py_name} {{}};\n"

    def get_class_cpp_def_code(self, class_py_name):
        return ""


def test_generator_pre_code_follows_alias_typedef():
    """A custom generator's pre-code is emitted after the alias typedef.

    Regression test for issue #30: the generator's pre-code refers to the class
    by its wrapper alias, so the `typedef <cpp> <py>;` (emitted in the shared
    preamble) must precede it. Emitting the pre-code first left the alias
    undeclared and failed to compile (seen on pychaste's CellsGenerator).
    """
    enum = _FakeEnum("Value", [("A", 0)])
    decl = _FakeStructDecl("Foo", "/src/Foo.hpp", enum)
    class_info = _FakeClassInfo(
        "Foo",
        decl,
        attrs={"common_include_file": True},
        source_file="Foo.hpp",
        cpp_names=["Foo<2>"],
        py_names=["Foo_2"],
        generator=_FakeGenerator(),
    )
    writer = _make_writer(class_info)

    # write() hoists the alias typedef into the preamble; the generator pre-code
    # (which uses the alias) stays in the block that follows.
    cpp = writer.build_cpp_header("typedef Foo<2> Foo_2;\n")
    cpp += "\n" + writer.build_struct_enum_register(0)

    assert cpp.index("typedef Foo<2> Foo_2;") < cpp.index("class Foo_2_Overrides")


def test_includes_block_skips_non_string_source_include():
    """A mis-typed (non-string) source_includes entry is skipped, not crashed on."""
    class_info = _FakeClassInfo(
        "Foo",
        object(),
        {"common_include_file": False, "source_includes": [5, "<memory>"]},
        "Foo.hpp",
    )
    writer = _make_writer(class_info)

    assert writer.includes_block() == '#include <memory>\n#include "Foo.hpp"\n'


class _RelatedClass:
    """Stand-in for a pygccxml base's related_class."""

    def __init__(self, name, decl_string):
        self.name = name
        self.decl_string = decl_string


class _Base:
    """Stand-in for a pygccxml hierarchy_info_t (a base class entry)."""

    def __init__(self, related_class, access_type="public"):
        self.related_class = related_class
        self.access_type = access_type


class _BasesDecl:
    """Stand-in for a class_t exposing .bases."""

    def __init__(self, bases):
        self.bases = bases


def _external_bases_writer(external_bases):
    class_info = _FakeClassInfo(
        "X",
        object(),
        {"imports": ["mod"], "external_bases": external_bases},
        "X.hpp",
    )
    return _make_writer(class_info)


def test_bases_block_scalar_external_bases_does_not_substring_match():
    """A scalar external_bases is treated as one name, not a substring haystack."""
    class_decl = _BasesDecl([_Base(_RelatedClass("Foo", "::Foo"))])
    writer = _external_bases_writer("AbstractFoo")  # mis-typed scalar

    # "Foo" is a substring of "AbstractFoo" but must NOT match.
    assert writer.bases_block(class_decl) == ""


def test_bases_block_scalar_external_bases_matches_named_base():
    """A scalar external_bases still works as a single external base name."""
    class_decl = _BasesDecl([_Base(_RelatedClass("AbstractFoo", "::AbstractFoo"))])
    writer = _external_bases_writer("AbstractFoo")

    assert writer.bases_block(class_decl) == ", ::AbstractFoo"


def test_bases_block_non_string_scalar_external_bases_is_ignored():
    """A non-string scalar external_bases is ignored, not crashed on."""
    class_decl = _BasesDecl([_Base(_RelatedClass("Foo", "::Foo"))])
    writer = _external_bases_writer(5)  # mis-typed non-string scalar

    assert writer.bases_block(class_decl) == ""


def test_bases_block_qualified_external_base_matches_unqualified_name():
    """A namespace-qualified external_bases entry matches the unqualified base name.

    pygccxml reports the base's name unqualified, so a qualified config entry
    must still match.
    """
    class_decl = _BasesDecl([_Base(_RelatedClass("AbstractFoo", "::ns::AbstractFoo"))])
    writer = _external_bases_writer(["ns::AbstractFoo"])

    assert writer.bases_block(class_decl) == ", ::ns::AbstractFoo"


# --- typecasters ---------------------------------------------------------

# The three casters used by examples/cells, matched against the types as they
# appear in generated registration text.
_PETSC = {"header": "caster_petsc.h", "types": ["Vec", "Mat"]}
_VTK = {"header": "PybindVTKTypeCaster.h", "types": ["vtkSmartPointer"]}
_UBLAS = {
    "header": "PybindUblasTypeCaster.hpp",
    "types": ["boost::numeric::ublas::c_vector"],
}


def _typecaster_writer(typecasters):
    class_info = _FakeClassInfo(
        "Foo",
        object(),
        {"common_include_file": False, "typecasters": typecasters},
        "Foo.hpp",
    )
    return _make_writer(class_info)


def test_detect_typecasters_matches_used_type():
    """A caster is selected when one of its types appears in the wrapper text."""
    writer = _typecaster_writer([_PETSC])
    scan = "(::Vec(*)(int)) &PetscUtils::CreateVec"

    assert writer._detect_typecasters(scan) == ["caster_petsc.h"]


def test_detect_typecasters_ignores_unused_caster():
    """A caster whose types are absent from the wrapper text is not selected."""
    writer = _typecaster_writer([_PETSC, _VTK])
    scan = "(unsigned int(Foo::*)() const) &Foo::GetIndex"

    assert writer._detect_typecasters(scan) == []


def test_detect_typecasters_boundary_aware():
    """Matching respects token boundaries, so `Vec` does not match `c_vector`.

    The ublas type must be matched by its own (namespace-qualified) name.
    """
    writer = _typecaster_writer([_PETSC, _UBLAS])
    scan = "(::boost::numeric::ublas::c_vector<double, 2>(Foo::*)()) &Foo::GetLocation"

    # `Vec` must NOT match the `c_vector` in the ublas type; only the ublas
    # caster is selected.
    assert writer._detect_typecasters(scan) == ["PybindUblasTypeCaster.hpp"]


def test_detect_typecasters_dedupes_and_preserves_order():
    """A header is emitted once, and headers follow config order."""
    writer = _typecaster_writer([_UBLAS, _PETSC])
    # Both PETSc types and the ublas type appear, ublas twice.
    scan = (
        "::Vec CreateVec; ::Mat CreateMat; "
        "::boost::numeric::ublas::c_vector<double,2> a; "
        "::boost::numeric::ublas::c_vector<double,3> b;"
    )

    # ublas is listed first in config, so it comes first; each header once.
    assert writer._detect_typecasters(scan) == [
        "PybindUblasTypeCaster.hpp",
        "caster_petsc.h",
    ]


def test_detect_typecasters_skips_malformed_entries():
    """Malformed typecasters entries are skipped without raising."""
    writer = _typecaster_writer(
        [
            "not-a-dict",  # not a dict
            {"types": ["Vec"]},  # missing header
            {"header": "empty.h", "types": []},  # no types
            {"header": "empty.h"},  # missing types
            _VTK,  # valid
        ]
    )
    scan = "::Vec v; ::vtkSmartPointer<vtkRenderer> r;"

    # Only the valid VTK entry is honoured; the malformed ones are dropped even
    # though `Vec` appears (its entry is missing a header).
    assert writer._detect_typecasters(scan) == ["PybindVTKTypeCaster.h"]


def test_detect_typecasters_no_config_returns_empty():
    """No typecasters config yields no includes."""
    writer = _typecaster_writer(None)

    assert writer._detect_typecasters("::Vec v;") == []


def test_includes_block_emits_typecasters_non_common():
    """Detected caster headers lead the non-common include block.

    Reproduces the examples/cells Node case: the caster is emitted right after
    the pybind headers, ahead of the package `<memory>` and the class header.
    """
    class_info = _FakeClassInfo(
        "Node",
        object(),
        {"common_include_file": False, "source_includes": ["<memory>"]},
        "Node.hpp",
    )
    writer = _make_writer(class_info)
    writer.typecaster_includes = ["PybindUblasTypeCaster.hpp"]

    assert writer.includes_block() == (
        '#include "PybindUblasTypeCaster.hpp"\n'
        "#include <memory>\n"
        '#include "Node.hpp"\n'
    )


def test_includes_block_emits_typecasters_common():
    """Detected caster headers follow the header collection in common mode."""
    class_info = _FakeClassInfo(
        "Node",
        object(),
        {"common_include_file": True},
        "Node.hpp",
    )
    writer = _make_writer(class_info)
    writer.typecaster_includes = ["caster_petsc.h"]

    assert writer.includes_block() == (
        '#include "wrapper_header_collection.cppwg.hpp"\n' '#include "caster_petsc.h"\n'
    )


def test_includes_block_emits_angle_bracket_typecaster():
    """A caster header spelled with angle brackets is emitted as a system include.

    A `typecasters.header` value like `<petsc/caster_petsc.h>` must become
    `#include <petsc/caster_petsc.h>`, not `#include "<petsc/caster_petsc.h>"`,
    matching how source_includes handles the `<...>` form.
    """
    # non-common branch
    class_info = _FakeClassInfo(
        "Node",
        object(),
        {"common_include_file": False},
        "Node.hpp",
    )
    writer = _make_writer(class_info)
    writer.typecaster_includes = ["<petsc/caster_petsc.h>"]
    assert writer.includes_block() == (
        "#include <petsc/caster_petsc.h>\n" '#include "Node.hpp"\n'
    )

    # common branch
    class_info = _FakeClassInfo(
        "Node",
        object(),
        {"common_include_file": True},
        "Node.hpp",
    )
    writer = _make_writer(class_info)
    writer.typecaster_includes = ["<petsc/caster_petsc.h>"]
    assert writer.includes_block() == (
        '#include "wrapper_header_collection.cppwg.hpp"\n'
        "#include <petsc/caster_petsc.h>\n"
    )
