"""Unit tests for cppwg.parsers.package_info_parser."""

import logging
import os
import textwrap

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
        "calldef_excludes" in record.message and "deprecated" in record.message.lower()
        for record in caplog.records
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

    assert not any("deprecated" in record.message.lower() for record in caplog.records)
