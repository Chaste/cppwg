"""Unit tests for cppwg.parsers.package_info_parser."""

import logging
import os
import textwrap

import pytest

from cppwg.parsers.package_info_parser import PackageInfoParser


def _write_config(tmp_path, body):
    """Write a package info yaml file and return its path."""
    config_path = os.path.join(tmp_path, "package_info.yaml")
    with open(config_path, "w") as config_file:
        config_file.write(textwrap.dedent(body))
    return config_path


def test_parses_explicit_free_function_list(tmp_path):
    """An explicit free_functions list is parsed without error.

    Regression test: the parser previously raised KeyError('name') for any
    explicitly listed free function, so the explicit free_functions path always
    crashed before reaching the C++ source.
    """
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            free_functions:
              - name: my_func
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.use_all_free_functions is False
    assert [ff.name for ff in module_info.free_function_collection] == ["my_func"]


def test_parses_all_free_functions_option(tmp_path):
    """The CPPWG_ALL free_functions option sets use_all_free_functions."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            free_functions: CPPWG_ALL
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.use_all_free_functions is True
    # Discovery happens later from the parsed source, so none are added yet.
    assert module_info.free_function_collection == []


def test_parses_module_imports(tmp_path):
    """A module-level `imports` list is parsed onto the module info."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            imports:
              - testpkg.othermod._testpkg_othermod
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.imports == ["testpkg.othermod._testpkg_othermod"]


def test_module_imports_default_to_empty_list(tmp_path):
    """A module's `imports` defaults to an empty list when not set."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.imports == []


def test_parses_package_typecasters(tmp_path):
    """A package-level `typecasters` list is parsed onto the package info."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        typecasters:
          - header: caster_petsc.h
            types: [Vec, Mat]
          - header: PybindVTKTypeCaster.h
            types: [vtkSmartPointer]
        modules:
          - name: mymod
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    assert package_info.typecasters == [
        {"header": "caster_petsc.h", "types": ["Vec", "Mat"]},
        {"header": "PybindVTKTypeCaster.h", "types": ["vtkSmartPointer"]},
    ]


def test_package_typecasters_default_to_empty_list(tmp_path):
    """A package's `typecasters` defaults to an empty list when not set."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    assert package_info.typecasters == []


def test_parses_class_auto_includes(tmp_path):
    """A class-level `auto_includes` flag is parsed onto the class info."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            classes:
              - name: Foo
                auto_includes: True
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    cls = package_info.module_collection[0].class_collection[0]
    assert cls.auto_includes is True


def test_class_auto_includes_defaults_to_none(tmp_path):
    """`auto_includes` defaults to None (inherit / off) when not set."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            classes:
              - name: Foo
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    cls = package_info.module_collection[0].class_collection[0]
    assert cls.auto_includes is None


def test_parses_module_external_bases(tmp_path):
    """A module-level `external_bases` list is parsed onto the module info."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            external_bases:
              - AbstractForce
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.external_bases == ["AbstractForce"]


def test_module_external_bases_default_to_empty_list(tmp_path):
    """A module's `external_bases` defaults to an empty list when not set."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.external_bases == []


def test_calldef_excludes_emits_deprecation_warning(tmp_path, caplog):
    """A deprecated calldef_excludes option triggers a deprecation warning."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            classes:
              - name: Foo
                calldef_excludes:
                  - double
        """,
    )

    with caplog.at_level(logging.WARNING):
        PackageInfoParser(config_path, str(tmp_path)).parse()

    assert any(
        "calldef_excludes" in message and "deprecated" in message.lower()
        for message in caplog.messages
    )


def test_no_deprecation_warning_for_current_options(tmp_path, caplog):
    """The replacement option arg_type_excludes does not warn."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            classes:
              - name: Foo
                arg_type_excludes:
                  - double
        """,
    )

    with caplog.at_level(logging.WARNING):
        PackageInfoParser(config_path, str(tmp_path)).parse()

    assert not any("deprecated" in message.lower() for message in caplog.messages)


def test_parses_exclude_inherited_overrides(tmp_path):
    """A package-level `exclude_inherited_overrides: True` is parsed as a bool."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        exclude_inherited_overrides: True
        modules:
          - name: mymod
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    assert package_info.exclude_inherited_overrides is True


def test_exclude_inherited_overrides_defaults_to_false(tmp_path):
    """`exclude_inherited_overrides` defaults to False when not set."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    assert package_info.exclude_inherited_overrides is False


def test_module_source_locations_converted_to_full_paths(tmp_path):
    """Module source_locations are resolved to absolute paths and verified."""
    (tmp_path / "src").mkdir()
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            source_locations:
              - src
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    expected = os.path.abspath(os.path.join(str(tmp_path), "src"))
    assert module_info.source_locations == [expected]


def test_verify_path_raises_for_missing_source_location(tmp_path):
    """A source_location that does not exist raises FileNotFoundError."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            source_locations:
              - does_not_exist
        """,
    )

    with pytest.raises(FileNotFoundError):
        PackageInfoParser(config_path, str(tmp_path)).parse()


def test_parses_module_variables(tmp_path):
    """An explicit variables list is parsed onto the module.

    The variable has no source_file_path, exercising the empty-path branch of
    full_path/verify_path.
    """
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            variables:
              - name: my_var
                source_file: my_var.hpp
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert [v.name for v in module_info.variable_collection] == ["my_var"]
    assert module_info.variable_collection[0].source_file == "my_var.hpp"


def test_custom_generator_path_converted_and_loaded(tmp_path):
    """A class custom_generator with a CPPWG_SOURCEROOT placeholder is resolved."""
    (tmp_path / "FooGen.py").write_text("class FooGen:\n    pass\n")
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            classes:
              - name: Foo
                custom_generator: CPPWG_SOURCEROOT/FooGen.py
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    cls = package_info.module_collection[0].class_collection[0]
    assert cls.custom_generator == os.path.abspath(str(tmp_path / "FooGen.py"))
    assert type(cls.custom_generator_instance).__name__ == "FooGen"


def test_free_function_source_file_is_applied(tmp_path):
    """A free function's source_file is copied from the raw config."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            free_functions:
              - name: my_func
                source_file: my_func.hpp
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    free_function = package_info.module_collection[0].free_function_collection[0]
    assert free_function.source_file == "my_func.hpp"


def test_convert_path_empty_returns_empty(tmp_path):
    """convert_path leaves an empty path empty rather than abspath-ing cwd."""
    config = _write_config(tmp_path, "name: pkg\nmodules:\n  - name: m\n")
    parser = PackageInfoParser(config, str(tmp_path))
    assert parser.convert_path("") == ""


def test_use_all_classes_skips_explicit_class_parsing(tmp_path):
    """A CPPWG_ALL classes option skips the explicit-class loop."""
    config = _write_config(
        tmp_path,
        "name: pkg\nmodules:\n  - name: m\n    classes: CPPWG_ALL\n",
    )
    package_info = PackageInfoParser(config, str(tmp_path)).parse()
    module = package_info.module_collection[0]
    assert module.use_all_classes is True
    assert module.class_collection == []


def test_parses_module_exclude_inherited_overrides(tmp_path):
    """A module-level `exclude_inherited_overrides` flag is parsed onto the module."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            exclude_inherited_overrides: True
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.exclude_inherited_overrides is True


def test_parses_class_exclude_inherited_overrides(tmp_path):
    """A class-level `exclude_inherited_overrides` flag is parsed onto the class."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        modules:
          - name: mymod
            classes:
              - name: Foo
                exclude_inherited_overrides: True
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    cls = package_info.module_collection[0].class_collection[0]
    assert cls.exclude_inherited_overrides is True


def test_module_exclude_inherited_overrides_defaults_to_none(tmp_path):
    """Unset at module level, the flag is None so it inherits from the package."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        exclude_inherited_overrides: True
        modules:
          - name: mymod
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.exclude_inherited_overrides is None
    # The package-level True is found by walking up the hierarchy.
    assert module_info.hierarchy_attribute("exclude_inherited_overrides") is True


def test_module_exclude_inherited_overrides_overrides_package(tmp_path):
    """A module-level False shadows a package-level True for its classes."""
    config_path = _write_config(
        tmp_path,
        """
        name: testpkg
        exclude_inherited_overrides: True
        modules:
          - name: mymod
            exclude_inherited_overrides: False
        """,
    )

    package_info = PackageInfoParser(config_path, str(tmp_path)).parse()

    module_info = package_info.module_collection[0]
    assert module_info.hierarchy_attribute("exclude_inherited_overrides") is False
