"""Unit tests for cppwg.writers.class_writer."""

from pygccxml import declarations

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
        self.auto_include_headers = []
        self.prefix_code = []
        self.suffix_code = []
        self.custom_generator_instance = generator
        self._name_base = name_base or name
        self._attrs = attrs
        # Consulted by CppMethodWrapperWriter.method_is_excluded.
        self.excluded_methods = []

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

    def get_class_cpp_source_includes(self, *args, **kwargs):
        return []


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

# The three casters used by examples/cells, as the already-validated
# (header, types) tuples the writer consumes (PackageInfo.parsed_typecasters
# does the parsing/validation once, upstream of the writer).
_PETSC = ("caster_petsc.h", ["Vec", "Mat"])
_VTK = ("PybindVTKTypeCaster.h", ["vtkSmartPointer"])
_UBLAS = ("PybindUblasTypeCaster.hpp", ["boost::numeric::ublas::c_vector"])


def _typecaster_writer(parsed_typecasters):
    class_info = _FakeClassInfo(
        "Foo",
        object(),
        {"common_include_file": False, "parsed_typecasters": parsed_typecasters},
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


def test_includes_block_dedups_caster_also_in_source_includes():
    """A caster listed under both typecasters and source_includes emits once.

    During migration a project may auto-detect a caster while still listing it
    manually under source_includes; the header must not be #included twice.
    """
    class_info = _FakeClassInfo(
        "Node",
        object(),
        {
            "common_include_file": False,
            # PybindUblasTypeCaster.hpp is still listed manually here as well.
            "source_includes": ["PybindUblasTypeCaster.hpp", "<memory>"],
        },
        "Node.hpp",
    )
    writer = _make_writer(class_info)
    writer.typecaster_includes = ["PybindUblasTypeCaster.hpp"]  # auto-detected too

    assert writer.includes_block() == (
        '#include "PybindUblasTypeCaster.hpp"\n'  # once, from the caster lead
        "#include <memory>\n"
        '#include "Node.hpp"\n'
    )


def test_includes_block_emits_auto_includes():
    """Auto-resolved project headers are emitted ahead of the class's own header."""
    class_info = _FakeClassInfo(
        "MeshFactory",
        object(),
        {"common_include_file": False},
        "MeshFactory.hpp",
    )
    writer = _make_writer(class_info)
    writer.class_info.auto_include_headers = ["PottsMesh.hpp"]

    assert writer.includes_block() == (
        '#include "PottsMesh.hpp"\n#include "MeshFactory.hpp"\n'
    )


def test_includes_block_dedups_auto_include_with_source_include():
    """A header that is both auto-resolved and listed manually emits once."""
    class_info = _FakeClassInfo(
        "MeshFactory",
        object(),
        {
            "common_include_file": False,
            "source_includes": ["PottsMesh.hpp", "<memory>"],
        },
        "MeshFactory.hpp",
    )
    writer = _make_writer(class_info)
    writer.class_info.auto_include_headers = ["PottsMesh.hpp"]

    assert writer.includes_block() == (
        '#include "PottsMesh.hpp"\n'  # once, from the auto-include lead
        "#include <memory>\n"
        '#include "MeshFactory.hpp"\n'
    )


class _SourceIncludeGen:
    """Custom generator that declares headers its generated code needs."""

    def __init__(self, headers):
        self._headers = headers

    def get_class_cpp_source_includes(self, *args, **kwargs):
        return self._headers


def test_includes_block_emits_generator_source_includes():
    """A custom generator's get_class_cpp_source_includes() headers are added to the block.

    Covers the category the auto-include detection cannot see: types named only
    in the generator's emitted code (e.g. GetAreaIn<SquareMetres>), whose
    headers the generator supplies itself. Angle-bracket and quoted forms both
    work.
    """
    class_info = _FakeClassInfo(
        "Foo",
        object(),
        {"common_include_file": False},
        "Foo.hpp",
        generator=_SourceIncludeGen(["Helper.hpp", "<memory>"]),
    )
    writer = _make_writer(class_info)

    assert writer.includes_block() == (
        '#include "Helper.hpp"\n' "#include <memory>\n" '#include "Foo.hpp"\n'
    )


def test_includes_block_dedups_generator_and_source_includes():
    """A header from both source_includes and the generator emits once."""
    class_info = _FakeClassInfo(
        "Foo",
        object(),
        {"common_include_file": False, "source_includes": ["Shared.hpp"]},
        "Foo.hpp",
        generator=_SourceIncludeGen(["Shared.hpp"]),
    )
    writer = _make_writer(class_info)

    assert writer.includes_block() == (
        '#include "Shared.hpp"\n'  # once (generator emits first, source_includes deduped)
        '#include "Foo.hpp"\n'
    )


def test_includes_block_generator_without_source_includes_hook():
    """A legacy generator lacking get_class_cpp_source_includes() does not break generation.

    Generators that only implement the pre/def-code methods (and do not subclass
    Custom) must keep working - the optional hook is skipped, not required.
    """

    class LegacyGen:
        def get_class_cpp_pre_code(self, *args):
            return ""

        def get_class_cpp_def_code(self, *args):
            return ""

    class_info = _FakeClassInfo(
        "Foo",
        object(),
        {"common_include_file": False},
        "Foo.hpp",
        generator=LegacyGen(),
    )
    writer = _make_writer(class_info)

    # No AttributeError; just the class's own header.
    assert writer.includes_block() == '#include "Foo.hpp"\n'


def test_includes_block_emits_generator_source_includes_in_common():
    """Generator get_class_cpp_source_includes() headers are emitted even in common mode.

    They can be <...> system headers or category-D headers (named only in the
    generator's emitted code) that wrapper_header_collection.cppwg.hpp does not
    pull in, so - like caster headers - they follow the header collection rather
    than being dropped at the common-include early return.
    """
    class_info = _FakeClassInfo(
        "Foo",
        object(),
        {"common_include_file": True},
        "Foo.hpp",
        generator=_SourceIncludeGen(["Writer.hpp", "<memory>"]),
    )
    writer = _make_writer(class_info)

    assert writer.includes_block() == (
        '#include "wrapper_header_collection.cppwg.hpp"\n'
        '#include "Writer.hpp"\n'
        "#include <memory>\n"
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


# ---------------------------------------------------------------------------
# exclude_inherited_overrides: _is_inherited_override predicate
# ---------------------------------------------------------------------------


class _FakeArgType:
    """Stand-in for a pygccxml argument type."""

    def __init__(self, decl_string):
        self.decl_string = decl_string


class _FakeMethodDecl:
    """Stand-in for a pygccxml member_function_t."""

    def __init__(
        self,
        name,
        virtuality="virtual",
        arg_types=(),
        has_const=False,
        access_type="public",
        return_type="void",
    ):
        self.name = name
        self.virtuality = virtuality
        self.argument_types = [_FakeArgType(t) for t in arg_types]
        self.has_const = has_const
        self.access_type = access_type
        # Needed by CppMethodWrapperWriter.method_is_excluded (the overload-
        # shadowing guard). parent is set by the owning _FakeDerivedDecl.
        self.return_type = _FakeArgType(return_type)
        self.parent = None


class _FakeBaseDecl:
    """Stand-in for a base class_t answering member_functions(name)."""

    def __init__(self, methods=()):
        self._methods = list(methods)
        # Own the methods, so method_is_excluded's parent check (used when the
        # base's own exclusion is consulted) treats them as this base's members.
        for method in self._methods:
            method.parent = self

    def member_functions(self, name=None, allow_empty=False):
        return [m for m in self._methods if name is None or m.name == name]


class _FakeHierarchyInfo:
    """Stand-in for a pygccxml hierarchy_info_t."""

    def __init__(self, related_class):
        self.related_class = related_class


class _FakeDerivedDecl:
    """Stand-in for the derived class_t exposing recursive_bases and own methods."""

    def __init__(self, bases=(), methods=()):
        self.recursive_bases = [_FakeHierarchyInfo(b) for b in bases]
        self._methods = list(methods)
        # Own the methods, so method_is_excluded's parent check treats them as
        # this class's members (not sub-class/iterator methods).
        for method in self._methods:
            method.parent = self

    def member_functions(self, name=None, function=None, allow_empty=False):
        result = [m for m in self._methods if name is None or m.name == name]
        # Honour the `function` predicate as pygccxml does. Production passes
        # access_type_matcher_t("public"); that matcher needs a real class_t
        # parent to call, so instead read its target access_type and filter on
        # each method's own access_type. Non-public overloads are then excluded
        # here, exactly as pygccxml would, rather than leaking into the caller's
        # overload-shadowing scan.
        if function is not None:
            target = getattr(function, "access_type", None)
            if target is not None:
                result = [m for m in result if m.access_type == target]
        return result


class _FakeBaseInfo:
    """Minimal class_info carrying the base's own wrapping-exclusion config."""

    def __init__(self, excluded_methods=(), excludes=None):
        self.excluded_methods = list(excluded_methods)
        # return_type_excludes / arg_type_excludes / calldef_excludes, keyed by
        # name, as CppMethodWrapperWriter.method_is_excluded gathers them.
        self._excludes = excludes or {}

    def hierarchy_attribute_gather_flat(self, name):
        return list(self._excludes.get(name, []))


def _override_writer(enabled, base_decl, base_info=None, attrs=None, same_module=True):
    """A class writer with the option set and a base wired into the package.

    By default the base is in the same module as the derived class (the common
    case, where the pybind base link is always emitted). Pass same_module=False
    to model a base wrapped in another module of the package; then whether the
    override is skippable depends on cross-module inheritance being enabled via
    an `imports` entry (see attrs).
    """
    class_attrs = {"exclude_inherited_overrides": enabled}
    if attrs:
        class_attrs.update(attrs)
    class_info = _FakeClassInfo(
        "Derived",
        object(),
        class_attrs,
        "Derived.hpp",
    )
    module_classes = {base_decl: "Base"} if same_module else {}
    writer = CppClassWrapperWriter(
        class_info, template_collection, module_classes=module_classes
    )
    writer.package_classes = {base_decl}
    if base_info is not None:
        writer.package_class_infos = {base_decl: base_info}
    return writer


def test_inherited_override_skipped_when_base_wraps_matching_virtual():
    """A virtual override of a wrapped base virtual is flagged for skipping."""
    base = _FakeBaseDecl([_FakeMethodDecl("GetNumNodes")])
    writer = _override_writer(True, base)
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetNumNodes")
    assert writer._is_inherited_override(class_decl, method) is True


def test_inherited_override_kept_when_option_off():
    """With the option off the method is never skipped."""
    base = _FakeBaseDecl([_FakeMethodDecl("GetNumNodes")])
    writer = _override_writer(False, base)
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetNumNodes")
    assert writer._is_inherited_override(class_decl, method) is False


def test_inherited_override_kept_when_base_excludes_method():
    """If the base excludes the method it is unwrapped there, so keep the override."""
    base = _FakeBaseDecl([_FakeMethodDecl("GetNumNodes")])
    base_info = _FakeBaseInfo(excluded_methods=["GetNumNodes"])
    writer = _override_writer(True, base, base_info)
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetNumNodes")
    assert writer._is_inherited_override(class_decl, method) is False


def test_inherited_override_kept_when_base_virtual_excluded_by_return_type():
    """A base virtual excluded by return type isn't wrapped, so keep the override.

    The base declares a matching virtual, but the base's own wrapper drops it via
    return_type_excludes (CppMethodWrapperWriter.method_is_excluded), so the base
    emits no binding. Skipping the derived override would remove the method's only
    Python-visible binding, so it must be kept.
    """
    base = _FakeBaseDecl([_FakeMethodDecl("GetPtr", return_type="RawPtr *")])
    base_info = _FakeBaseInfo(excludes={"return_type_excludes": ["RawPtr"]})
    writer = _override_writer(True, base, base_info)
    class_decl = _FakeDerivedDecl(bases=[base])
    # Covariant override (return type not compared), same name/args/const-ness.
    method = _FakeMethodDecl("GetPtr", return_type="DerivedPtr *")
    assert writer._is_inherited_override(class_decl, method) is False


def test_inherited_override_kept_for_non_virtual_method():
    """A non-virtual same-name method is not an override and is not skipped."""
    base = _FakeBaseDecl([_FakeMethodDecl("GetNumNodes")])
    writer = _override_writer(True, base)
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetNumNodes", virtuality="not virtual")
    assert writer._is_inherited_override(class_decl, method) is False


def test_inherited_override_kept_when_base_not_wrapped():
    """An unwrapped base provides no binding to inherit, so keep the override."""
    base = _FakeBaseDecl([_FakeMethodDecl("GetNumNodes")])
    writer = _override_writer(True, base)
    writer.package_classes = set()  # base not wrapped anywhere
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetNumNodes")
    assert writer._is_inherited_override(class_decl, method) is False


def test_inherited_override_distinguishes_overloads_by_args():
    """A same-name base virtual with different args is a different overload."""
    base = _FakeBaseDecl([_FakeMethodDecl("GetNode", arg_types=["unsigned int"])])
    writer = _override_writer(True, base)
    class_decl = _FakeDerivedDecl(bases=[base])
    # Derived declares an overload with an extra argument.
    method = _FakeMethodDecl("GetNode", arg_types=["unsigned int", "double"])
    assert writer._is_inherited_override(class_decl, method) is False


def test_inherited_override_matches_regardless_of_return_type():
    """Return type is not compared, so a covariant-return override still matches."""
    base = _FakeBaseDecl([_FakeMethodDecl("GetMesh", arg_types=[], has_const=True)])
    writer = _override_writer(True, base)
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetMesh", arg_types=[], has_const=True)
    assert writer._is_inherited_override(class_decl, method) is True


def test_inherited_override_kept_when_sibling_overload_survives():
    """A redundant override is kept if another same-name overload would bind.

    pybind11 resolves overloads by name, so a derived binding of a name shadows
    the inherited base binding. If the class still binds a sibling overload, the
    override must be kept - otherwise that override would become unreachable.
    """
    base = _FakeBaseDecl(
        [_FakeMethodDecl("GetLineTensionParameter", arg_types=["int", "int"])]
    )
    writer = _override_writer(True, base)
    override = _FakeMethodDecl("GetLineTensionParameter", arg_types=["int", "int"])
    # A 0-arg non-virtual overload that is NOT a redundant override, so it would
    # still be bound and shadow the base.
    sibling = _FakeMethodDecl(
        "GetLineTensionParameter", virtuality="not virtual", arg_types=[]
    )
    class_decl = _FakeDerivedDecl(bases=[base], methods=[override, sibling])
    assert writer._is_inherited_override(class_decl, override) is False


def test_inherited_override_skipped_when_sibling_overload_is_excluded():
    """An excluded same-name sibling emits no binding, so the override is skipped.

    The sibling overload is excluded from wrapping (here via arg_type_excludes),
    so it produces no `.def` and cannot shadow the inherited base overloads.
    Without filtering it out, the guard would treat it as a surviving binding and
    wrongly keep the redundant override - which would itself shadow the base.
    """
    base = _FakeBaseDecl([_FakeMethodDecl("foo", arg_types=["int"])])
    writer = _override_writer(True, base, attrs={"arg_type_excludes": ["BadType"]})
    override = _FakeMethodDecl("foo", arg_types=["int"])
    # A non-override overload that will be excluded from wrapping by its arg type.
    excluded_sibling = _FakeMethodDecl(
        "foo", virtuality="not virtual", arg_types=["BadType"]
    )
    class_decl = _FakeDerivedDecl(bases=[base], methods=[override, excluded_sibling])
    assert writer._is_inherited_override(class_decl, override) is True


def test_inherited_override_skipped_when_all_overloads_are_overrides():
    """If every same-name overload is a redundant override, all are skipped."""
    base = _FakeBaseDecl(
        [
            _FakeMethodDecl("foo", arg_types=[]),
            _FakeMethodDecl("foo", arg_types=["int"]),
        ]
    )
    writer = _override_writer(True, base)
    foo0 = _FakeMethodDecl("foo", arg_types=[])
    foo1 = _FakeMethodDecl("foo", arg_types=["int"])
    class_decl = _FakeDerivedDecl(bases=[base], methods=[foo0, foo1])
    assert writer._is_inherited_override(class_decl, foo0) is True
    assert writer._is_inherited_override(class_decl, foo1) is True


def test_inherited_override_skipped_despite_non_public_sibling_overload():
    """A non-public same-name overload does not block skipping the override.

    Only public methods are bound, so a protected/private overload of the same
    name cannot shadow the inherited base binding. The overload-shadowing guard
    scans public overloads only (access_type_matcher_t("public")), so such a
    sibling is filtered out and the redundant public override is still skipped.
    This case only passes when the fake honours that predicate.
    """
    base = _FakeBaseDecl([_FakeMethodDecl("foo", arg_types=[])])
    writer = _override_writer(True, base)
    override = _FakeMethodDecl("foo", arg_types=[])
    # A protected overload that is NOT a redundant override; if the public filter
    # were ignored it would be seen as a surviving binding and keep the override.
    protected_sibling = _FakeMethodDecl(
        "foo", virtuality="not virtual", arg_types=["int"], access_type="protected"
    )
    class_decl = _FakeDerivedDecl(bases=[base], methods=[override, protected_sibling])
    assert writer._is_inherited_override(class_decl, override) is True


def test_inherited_override_kept_when_base_in_other_module_without_imports():
    """A cross-module base without `imports` provides no inherited binding.

    bases_block only links a base wrapped in another module into the derived
    py::class_ when cross-module inheritance is enabled (`imports` set). Without
    that link the base binding is not inherited, so the override is the sole
    binding and must be kept.
    """
    base = _FakeBaseDecl([_FakeMethodDecl("GetNumNodes")])
    # Base wrapped elsewhere in the package (package_classes) but NOT in this
    # module, and imports is unset.
    writer = _override_writer(True, base, same_module=False)
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetNumNodes")
    assert writer._is_inherited_override(class_decl, method) is False


def test_inherited_override_skipped_when_base_in_other_module_with_imports():
    """A cross-module base with `imports` set is linked, so the override is skipped.

    With cross-module inheritance enabled the base link is emitted and its
    binding is inherited, making the derived override redundant.
    """
    base = _FakeBaseDecl([_FakeMethodDecl("GetNumNodes")])
    writer = _override_writer(
        True, base, attrs={"imports": ["othermod"]}, same_module=False
    )
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetNumNodes")
    assert writer._is_inherited_override(class_decl, method) is True


def test_inherited_override_kept_when_base_virtual_not_public():
    """A protected/private base virtual is not wrapped, so keep the override.

    Only public methods get a binding, so a same-signature virtual that is
    protected on the base provides no inherited binding - dropping the override
    would make it unreachable.
    """
    base = _FakeBaseDecl([_FakeMethodDecl("GetValue", access_type="protected")])
    writer = _override_writer(True, base)
    class_decl = _FakeDerivedDecl(bases=[base])
    method = _FakeMethodDecl("GetValue")  # public override
    assert writer._is_inherited_override(class_decl, method) is False


class _CWType:
    def __init__(self, decl_string):
        self.decl_string = decl_string


class _CWArg:
    def __init__(self, name):
        self.name = name


class _CWMethod:
    def __init__(
        self,
        name,
        return_type="void",
        virtuality="virtual",
        arg_types=(),
        arguments=(),
        has_const=False,
        parent=None,
        access="public",
    ):
        self.name = name
        self.return_type = _CWType(return_type)
        self.virtuality = virtuality
        self.argument_types = [_CWType(a) for a in arg_types]
        self.arguments = list(arguments)
        self.has_const = has_const
        self.access_type = access
        self.parent = parent


class _CWClassDecl:
    def __init__(self, name, methods=()):
        self.name = name
        self._methods = list(methods)

    def member_functions(self, function=None, allow_empty=True):
        return self._methods


def _class_writer_with_methods(methods):
    class_decl = _CWClassDecl("Foo", methods)
    for method in methods:
        method.parent = class_decl
    class_info = _FakeClassInfo("Foo", class_decl, {}, "Foo.hpp", py_names=["Foo"])
    class_info.template_params = None
    class_info.template_arg_lists = None
    return _make_writer(class_info)


def test_virtual_overrides_builds_trampoline_and_typedefs():
    """Virtual methods produce a trampoline class and return-type typedefs."""
    methods = [
        _CWMethod("area", return_type="double", virtuality="pure virtual"),
        _CWMethod("clone", return_type="::Bar<2> *", virtuality="virtual"),
        _CWMethod("helper", return_type="void", virtuality="not virtual"),
    ]
    writer = _class_writer_with_methods(methods)

    return_typedefs, override_class, methods_needing_override = (
        writer.virtual_overrides(0)
    )

    assert [m.name for m in methods_needing_override] == ["area", "clone"]
    # The special-character return type gets a typedef; "double"/"void" do not.
    assert "typedef ::Bar<2> *" in return_typedefs
    assert "double" not in return_typedefs
    assert "PYBIND11_OVERRIDE_PURE" in override_class  # from the pure-virtual method
    assert "PYBIND11_OVERRIDE(" in override_class  # from the plain virtual method


def test_virtual_overrides_empty_without_virtual_methods():
    """A class with no virtual methods needs no trampoline."""
    writer = _class_writer_with_methods([_CWMethod("helper", virtuality="not virtual")])
    return_typedefs, override_class, methods_needing_override = (
        writer.virtual_overrides(0)
    )
    assert return_typedefs == ""
    assert override_class == ""
    assert methods_needing_override == []


import pytest  # noqa: E402

from cppwg.writers import class_writer as class_writer_module  # noqa: E402


def test_construction_rejects_mismatched_instantiation_lists():
    """__init__ validates that decls, cpp_names and py_names are parallel."""
    decl = _FakeStructDecl("Foo", "/src/Foo.hpp", _FakeEnum("V", [("A", 0)]))
    class_info = _FakeClassInfo(
        "Foo", decl, {}, "Foo.hpp", cpp_names=["Foo"], py_names=["Foo", "Extra"]
    )
    with pytest.raises(AssertionError):
        _make_writer(class_info)


def test_write_raises_on_mismatched_instantiation_lists(tmp_path):
    """write() re-validates the lists in case they were mutated after construction."""
    decl = _FakeStructDecl("Foo", "/src/Foo.hpp", _FakeEnum("V", [("A", 0)]))
    class_info = _FakeClassInfo("Foo", decl, {}, "Foo.hpp")
    class_info.template_params = None
    class_info.template_arg_lists = None
    writer = _make_writer(class_info)
    class_info.py_names = ["Foo", "Extra"]  # break the lockstep after construction
    with pytest.raises(AssertionError, match="mismatched"):
        writer.write(str(tmp_path))


def test_write_struct_enum_writes_files(tmp_path, monkeypatch):
    """A struct wrapping a single enum is registered and its files written."""
    monkeypatch.setattr(
        class_writer_module.type_traits_classes, "is_struct", lambda decl: True
    )
    decl = _FakeStructDecl("Color", "/src/Color.hpp", _FakeEnum("Value", [("RED", 0)]))
    class_info = _FakeClassInfo("Color", decl, {}, "Color.hpp")
    class_info.template_params = None
    class_info.template_arg_lists = None

    _make_writer(class_info).write(str(tmp_path))

    assert (tmp_path / "Color.cppwg.hpp").is_file()
    assert (tmp_path / "Color.cppwg.cpp").is_file()


class _FakeVariable:
    """Stand-in for a pygccxml variable_t (public data member)."""

    def __init__(self, name, decl_type=None, bits=None, static=False):
        self.name = name
        self.decl_type = decl_type if decl_type is not None else declarations.double_t()
        self.bits = bits
        self.type_qualifiers = declarations.type_qualifiers_t()
        self.type_qualifiers.has_static = static


class _DataStructDecl:
    """Stand-in for a plain data struct decl (no enum), for the class path.

    Supports the parts build_class_register / virtual_overrides / bases_block
    consult: member functions, constructors, public data members and bases.
    """

    def __init__(self, name, file_name, variables=(), enums=()):
        self.name = name
        self.location = _FakeLocation(file_name)
        self._variables = list(variables)
        self._enums = list(enums)
        self.bases = []
        self.recursive_bases = []
        self.is_abstract = False

    def enumerations(self, allow_empty=False):
        return self._enums

    def member_functions(self, name=None, function=None, allow_empty=False):
        return []

    def constructors(self, function=None, allow_empty=False):
        return []

    def variables(self, function=None, allow_empty=False):
        return self._variables


def test_write_wraps_non_enum_struct_as_class(tmp_path, monkeypatch):
    """A plain data struct is wrapped as a normal class, with member bindings.

    Regression test for issue #116: previously any struct that was not the
    single-nested-enum pattern was silently dropped (no wrapper file), while the
    module writer still emitted its include/register call.
    """
    monkeypatch.setattr(
        class_writer_module.type_traits_classes, "is_struct", lambda decl: True
    )
    decl = _DataStructDecl(
        "Metrics",
        "/src/Metrics.hpp",
        variables=[
            _FakeVariable("area"),
            _FakeVariable(
                "dimension", decl_type=declarations.const_t(declarations.int_t())
            ),
        ],
    )
    class_info = _FakeClassInfo("Metrics", decl, {}, "Metrics.hpp")
    class_info.template_params = None
    class_info.template_arg_lists = None

    _make_writer(class_info).write(str(tmp_path))

    assert (tmp_path / "Metrics.cppwg.hpp").is_file()
    cpp = (tmp_path / "Metrics.cppwg.cpp").read_text()
    assert '.def_readwrite("area", &Metrics::area)' in cpp
    assert '.def_readonly("dimension", &Metrics::dimension)' in cpp


def test_build_class_register_skips_static_and_bitfield_members(tmp_path, monkeypatch):
    """Static and bitfield data members are not bound (no address to take)."""
    monkeypatch.setattr(
        class_writer_module.type_traits_classes, "is_struct", lambda decl: True
    )
    decl = _DataStructDecl(
        "Flags",
        "/src/Flags.hpp",
        variables=[
            _FakeVariable("shared", static=True),
            _FakeVariable("packed", bits=1),
            _FakeVariable("value"),
        ],
    )
    class_info = _FakeClassInfo("Flags", decl, {}, "Flags.hpp")
    class_info.template_params = None
    class_info.template_arg_lists = None

    _make_writer(class_info).write(str(tmp_path))

    cpp = (tmp_path / "Flags.cppwg.cpp").read_text()
    assert '.def_readwrite("value", &Flags::value)' in cpp
    assert "shared" not in cpp
    assert "packed" not in cpp


def test_write_struct_with_multiple_enums_wraps_as_class(tmp_path, monkeypatch):
    """A struct with more than one enum is wrapped as a class, not dropped."""
    monkeypatch.setattr(
        class_writer_module.type_traits_classes, "is_struct", lambda decl: True
    )
    decl = _DataStructDecl(
        "Multi",
        "/src/Multi.hpp",
        variables=[_FakeVariable("x")],
        enums=[_FakeEnum("A", [("P", 0)]), _FakeEnum("B", [("Q", 0)])],
    )
    class_info = _FakeClassInfo("Multi", decl, {}, "Multi.hpp")
    class_info.template_params = None
    class_info.template_arg_lists = None

    _make_writer(class_info).write(str(tmp_path))

    cpp = (tmp_path / "Multi.cppwg.cpp").read_text()
    assert "register_Multi_class" in cpp
    assert '.def_readwrite("x", &Multi::x)' in cpp


def test_write_wraps_plain_class_with_members(tmp_path, monkeypatch):
    """A non-struct class also takes the normal path and binds its members."""
    monkeypatch.setattr(
        class_writer_module.type_traits_classes, "is_struct", lambda decl: False
    )
    decl = _DataStructDecl("Widget", "/src/Widget.hpp", variables=[_FakeVariable("w")])
    class_info = _FakeClassInfo("Widget", decl, {}, "Widget.hpp")
    class_info.template_params = None
    class_info.template_arg_lists = None

    _make_writer(class_info).write(str(tmp_path))

    cpp = (tmp_path / "Widget.cppwg.cpp").read_text()
    assert "register_Widget_class" in cpp
    assert '.def_readwrite("w", &Widget::w)' in cpp


def test_write_warns_and_writes_nothing_when_no_register_blocks(tmp_path, caplog):
    """A class with no instantiations produces no file and logs a warning.

    The module writer still emits an include/register call for the class, so the
    empty result is surfaced as a warning rather than a silent missing file.
    """
    class_info = _FakeClassInfo(
        "Empty",
        decl=None,
        attrs={},
        source_file="Empty.hpp",
        cpp_names=[],
        py_names=[],
        decls=[],
    )
    class_info.template_params = None
    class_info.template_arg_lists = None

    with caplog.at_level("WARNING"):
        _make_writer(class_info).write(str(tmp_path))

    assert list(tmp_path.iterdir()) == []  # no files written
    assert "produced no wrapper code" in caplog.text


def test_includes_block_falls_back_to_decl_location_header():
    """With no source_file set, the class's own header comes from its decl."""
    decl = _FakeStructDecl("Foo", "/src/path/Foo.hpp", _FakeEnum("V", [("A", 0)]))
    class_info = _FakeClassInfo("Foo", decl, {}, source_file="")
    writer = _make_writer(class_info)
    assert '#include "Foo.hpp"\n' in writer.includes_block()


class _BaseHierarchy:
    def __init__(self, access_type, related_class):
        self.access_type = access_type
        self.related_class = related_class


class _ClassDeclWithBases:
    def __init__(self, bases):
        self.bases = bases


def test_bases_block_skips_private_base_and_uses_module_alias():
    """A private base is skipped; a base wrapped in this module uses its alias."""
    wrapped_base = object()
    class_decl = _ClassDeclWithBases(
        [
            _BaseHierarchy("private", object()),  # private -> skipped
            _BaseHierarchy("public", wrapped_base),  # wrapped here -> aliased
        ]
    )
    class_info = _FakeClassInfo("Foo", class_decl, {"external_bases": []}, "Foo.hpp")
    writer = CppClassWrapperWriter(
        class_info, template_collection, module_classes={wrapped_base: "Base_2"}
    )
    assert writer.bases_block(class_decl) == ", Base_2"
