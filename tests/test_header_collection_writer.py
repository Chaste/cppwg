"""Unit tests for cppwg.writers.header_collection_writer."""

import os

from cppwg.templates.pybind11_default import template_collection
from cppwg.writers.header_collection_writer import CppHeaderCollectionWriter


class _FakeClassInfo:
    """Minimal CppClassInfo stand-in for the header collection writer."""

    def __init__(
        self,
        name,
        source_file="",
        excluded=False,
        template_arg_lists=None,
        cpp_names=None,
        py_names=None,
    ):
        self.name = name
        self.source_file = source_file
        self.excluded = excluded
        self.template_arg_lists = template_arg_lists or []
        self.cpp_names = cpp_names or [name]
        self.py_names = py_names or [name]


class _FakeFreeFunctionInfo:
    """Minimal CppFreeFunctionInfo stand-in."""

    def __init__(self, name, source_file_path=""):
        self.name = name
        self.source_file_path = source_file_path


class _FakeModuleInfo:
    """Minimal ModuleInfo stand-in."""

    def __init__(
        self,
        classes=None,
        free_functions=None,
        enums=None,
        use_all_classes=False,
        use_all_free_functions=False,
        use_all_enums=False,
    ):
        self.class_collection = classes or []
        self.free_function_collection = free_functions or []
        self.enum_collection = enums or []
        self.use_all_classes = use_all_classes
        self.use_all_free_functions = use_all_free_functions
        self.use_all_enums = use_all_enums


class _FakePackageInfo:
    """Minimal PackageInfo stand-in."""

    def __init__(
        self,
        name,
        modules,
        prefix_text=None,
        source_hpp_files=None,
        exception_names=None,
    ):
        self.name = name
        self.module_collection = modules
        self._prefix_text = prefix_text
        self.source_hpp_files = source_hpp_files or []
        self._exception_names = exception_names or []

    def hierarchy_attribute(self, key):
        return self._prefix_text if key == "prefix_text" else None

    @property
    def exception_names(self):
        return self._exception_names


def _write(tmp_path, package_info):
    """Run the writer and return the generated header collection string."""
    writer = CppHeaderCollectionWriter(
        package_info,
        template_collection,
        wrapper_root=str(tmp_path),
        hpp_collection_file=os.path.join(
            str(tmp_path), "wrapper_header_collection.hpp"
        ),
    )
    writer.write()
    return writer.hpp_collection


def test_header_collection_specific_includes(tmp_path):
    """Specific-include mode lists per-class headers and template instantiations.

    Covers the branch used when modules wrap an explicit class list: only the
    headers of wrapped classes are included, and only templated classes produce
    instantiations and typedefs.
    """
    foo = _FakeClassInfo(
        "Foo",
        source_file="Foo.hpp",
        template_arg_lists=[[2, 2], [3, 3]],
        cpp_names=["Foo<2, 2>", "Foo<3, 3>"],
        py_names=["Foo_2_2", "Foo_3_3"],
    )
    bar = _FakeClassInfo("Bar", source_file="Bar.hpp")  # untemplated
    package_info = _FakePackageInfo(
        "testpkg",
        [_FakeModuleInfo(classes=[foo, bar])],
        prefix_text="// header",
    )

    output = _write(tmp_path, package_info)

    expected = (
        "// header\n"
        "#ifndef testpkg_HEADERS_HPP_\n"
        "#define testpkg_HEADERS_HPP_\n"
        "\n"
        "// Includes\n"
        '#include "Bar.hpp"\n'
        '#include "Foo.hpp"\n'
        "\n"
        "// Instantiate Template Classes\n"
        "template class Foo<2, 2>;\n"
        "template class Foo<3, 3>;\n"
        "\n"
        "// Typedefs for nicer naming\n"
        "namespace cppwg\n"
        "{\n"
        "    typedef Foo<2, 2> Foo_2_2;\n"
        "    typedef Foo<3, 3> Foo_3_3;\n"
        "} // namespace cppwg\n"
        "\n"
        "#endif // testpkg_HEADERS_HPP_\n"
    )
    assert output == expected


def test_header_collection_include_all(tmp_path):
    """Include-all mode lists every source header in order.

    Covers the branch taken when a module uses all classes/free functions: every
    file in source_hpp_files is included, regardless of the wrapped class list.
    """
    widget = _FakeClassInfo(
        "Widget",
        template_arg_lists=[[2], [3]],
        cpp_names=["Widget<2>", "Widget<3>"],
        py_names=["Widget_2", "Widget_3"],
    )
    package_info = _FakePackageInfo(
        "allpkg",
        [_FakeModuleInfo(classes=[widget], use_all_classes=True)],
        source_hpp_files=["/s/Alpha.hpp", "/s/Beta.hpp"],
    )

    output = _write(tmp_path, package_info)

    expected = (
        "#ifndef allpkg_HEADERS_HPP_\n"
        "#define allpkg_HEADERS_HPP_\n"
        "\n"
        "// Includes\n"
        '#include "Alpha.hpp"\n'
        '#include "Beta.hpp"\n'
        "\n"
        "// Instantiate Template Classes\n"
        "template class Widget<2>;\n"
        "template class Widget<3>;\n"
        "\n"
        "// Typedefs for nicer naming\n"
        "namespace cppwg\n"
        "{\n"
        "    typedef Widget<2> Widget_2;\n"
        "    typedef Widget<3> Widget_3;\n"
        "} // namespace cppwg\n"
        "\n"
        "#endif // allpkg_HEADERS_HPP_\n"
    )
    assert output == expected


def test_header_collection_excludes_classes_and_adds_ff_and_exception_headers(tmp_path):
    """Excluded classes are skipped; free-function and exception headers included."""
    included = _FakeClassInfo("Foo", source_file="Foo.hpp")
    excluded = _FakeClassInfo("Hidden", source_file="Hidden.hpp", excluded=True)
    free_function = _FakeFreeFunctionInfo(
        "my_func", source_file_path="/s/funcs/MyFunc.hpp"
    )

    exc_header = tmp_path / "MyError.hpp"
    exc_header.write_text("class MyError {};\n")
    # A second header after the exception one is left unscanned once every
    # exception has been found (the early break).
    other_header = tmp_path / "Other.hpp"
    other_header.write_text("class Other {};\n")

    package_info = _FakePackageInfo(
        "pkg",
        [
            _FakeModuleInfo(
                classes=[included, excluded], free_functions=[free_function]
            )
        ],
        source_hpp_files=[str(exc_header), str(other_header)],
        exception_names=["MyError"],
    )

    output = _write(tmp_path, package_info)

    assert '#include "Foo.hpp"' in output
    assert "Hidden.hpp" not in output  # excluded class skipped
    assert '#include "MyFunc.hpp"' in output  # free-function header
    assert '#include "MyError.hpp"' in output  # exception class header
