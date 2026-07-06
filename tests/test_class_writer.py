"""Unit tests for cppwg.writers.class_writer."""

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

    def __init__(self, name, decl, attrs, source_file):
        self.name = name
        self.cpp_names = [name]
        self.py_names = [name]
        self.decls = [decl]
        self.source_file = source_file
        self.prefix_code = []
        self.suffix_code = []
        self.custom_generator_instance = None
        self._attrs = attrs

    def hierarchy_attribute(self, key):
        return self._attrs.get(key)

    def hierarchy_attribute_gather(self, key):
        value = self._attrs.get(key)
        return [value] if value else []


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

    output = _make_writer(class_info).build_struct_enum_cpp(0)

    expected = (
        "#include <pybind11/pybind11.h>\n"
        "#include <pybind11/stl.h>\n"
        '#include "wrapper_header_collection.cppwg.hpp"\n'
        "\n"
        '#include "Color.cppwg.hpp"\n'
        "\n"
        "namespace py = pybind11;\n"
        "typedef Color Color;\n"
        "PYBIND11_DECLARE_HOLDER_TYPE(T, std::shared_ptr<T>);\n"
        "void register_Color_class(py::module &m){\n"
        '    py::class_<Color> myclass(m, "Color");\n'
        '    py::enum_<Color::Value>(myclass, "Value")\n'
        '        .value("RED", Color::Value::RED)\n'
        '        .value("GREEN", Color::Value::GREEN)\n'
        '        .value("BLUE", Color::Value::BLUE)\n'
        "    .export_values();\n"
        "}\n"
    )
    assert output == expected


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

    output = _make_writer(class_info).build_struct_enum_cpp(0)

    expected = (
        "// auto\n"
        "#include <pybind11/pybind11.h>\n"
        "#include <pybind11/stl.h>\n"
        "#include <memory>\n"
        '#include "Color.hpp"\n'
        "\n"
        '#include "Color.cppwg.hpp"\n'
        "\n"
        "namespace py = pybind11;\n"
        "typedef Color Color;\n"
        ";\n"
        "void register_Color_class(py::module &m){\n"
        '    py::class_<Color> myclass(m, "Color");\n'
        '    py::enum_<Color::Value>(myclass, "Value")\n'
        '        .value("RED", Color::Value::RED)\n'
        "    .export_values();\n"
        "}\n"
    )
    assert output == expected
