"""Unit tests for cppwg.generators construction."""

import os

import pytest

from cppwg import generators as generators_module
from cppwg.generators import CppWrapperGenerator


@pytest.fixture
def castxml_env(monkeypatch):
    """Mock castxml discovery/version so __init__ runs without a real binary."""
    monkeypatch.setattr(
        generators_module.pygccxml.utils,
        "find_xml_generator",
        lambda name=None: ("/fake/castxml", None),
    )
    monkeypatch.setattr(
        generators_module.subprocess,
        "check_output",
        lambda *args, **kwargs: b"castxml version 0.6.0",
    )
    monkeypatch.setattr(
        generators_module.shutil, "which", lambda name: "/usr/bin/clang++"
    )


def _generator(tmp_path, **overrides):
    kwargs = dict(source_root=str(tmp_path), wrapper_root=str(tmp_path / "wrap"))
    kwargs.update(overrides)
    return CppWrapperGenerator(**kwargs)


def test_finds_castxml_on_path_and_creates_wrapper_root(castxml_env, tmp_path):
    gen = _generator(tmp_path)
    assert gen.castxml_binary == "/fake/castxml"
    assert gen.castxml_keeps_defaulted_args is True  # castxml 0.6.0 keeps them
    assert (tmp_path / "wrap").is_dir()  # wrapper root created


def test_explicit_castxml_binary_is_used(castxml_env, tmp_path):
    binary = tmp_path / "castxml"
    binary.write_text("")
    binary.chmod(0o755)
    gen = _generator(tmp_path, castxml_binary=str(binary))
    assert gen.castxml_binary == str(binary)


def test_invalid_explicit_castxml_falls_back_to_search(castxml_env, tmp_path):
    gen = _generator(tmp_path, castxml_binary=str(tmp_path / "missing"))
    assert gen.castxml_binary == "/fake/castxml"  # warned, then found on path


def test_castxml_not_found_raises(castxml_env, tmp_path, monkeypatch):
    monkeypatch.setattr(
        generators_module.pygccxml.utils,
        "find_xml_generator",
        lambda name=None: (None, None),
    )
    with pytest.raises(FileNotFoundError):
        _generator(tmp_path)


def test_unparsable_castxml_version_assumes_no_defaulted_args(
    castxml_env, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        generators_module.subprocess,
        "check_output",
        lambda *args, **kwargs: b"castxml development build",
    )
    gen = _generator(tmp_path)
    assert gen.castxml_keeps_defaulted_args is False


def test_explicit_castxml_compiler_is_used(castxml_env, tmp_path):
    gen = _generator(tmp_path, castxml_compiler="/opt/gcc")
    assert gen.castxml_compiler == "/opt/gcc"


def test_no_clang_compiler_leaves_compiler_none(castxml_env, tmp_path, monkeypatch):
    monkeypatch.setattr(generators_module.shutil, "which", lambda name: None)
    gen = _generator(tmp_path)
    assert gen.castxml_compiler is None


def test_missing_source_root_raises(castxml_env, tmp_path):
    with pytest.raises(FileNotFoundError):
        CppWrapperGenerator(
            source_root=str(tmp_path / "nope"), wrapper_root=str(tmp_path / "wrap")
        )


def test_auto_wrapper_root_is_created_under_source_root(castxml_env, tmp_path):
    gen = _generator(tmp_path, wrapper_root=None)
    assert gen.wrapper_root.startswith(str(tmp_path))
    assert os.path.isdir(gen.wrapper_root)


def test_missing_source_include_dir_warns_but_keeps_it(castxml_env, tmp_path):
    missing = str(tmp_path / "noinc")
    gen = _generator(tmp_path, source_includes=[missing])
    assert gen.source_includes == [missing]


def test_missing_package_info_file_raises(castxml_env, tmp_path):
    with pytest.raises(FileNotFoundError):
        _generator(tmp_path, package_info_path=str(tmp_path / "no.yaml"))


def test_default_package_info_discovered_in_cwd(castxml_env, tmp_path, monkeypatch):
    (tmp_path / "package_info.yaml").write_text("name: pkg\n")
    monkeypatch.chdir(tmp_path)
    gen = _generator(tmp_path)
    assert gen.package_info_path.endswith("package_info.yaml")


def test_no_package_info_uses_default_settings(castxml_env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no package_info.yaml present
    gen = _generator(tmp_path)
    assert gen.package_info_path is None


def test_parse_package_info_uses_defaults_without_config(castxml_env, tmp_path):
    """With no package-info file, a default PackageInfo is created."""
    gen = _generator(tmp_path)
    gen.parse_package_info()
    assert gen.package_info.name == "cppwg_package"


def test_log_unknown_classes_reports_text_scanned_classes(castxml_env, tmp_path, caplog):
    """A source class that is wrapped nowhere is logged as unknown."""
    import logging
    from types import SimpleNamespace

    gen = _generator(tmp_path)
    (tmp_path / "Widget.hpp").write_text("class Widget {};\n")
    module = SimpleNamespace(class_collection=[], source_locations=[])
    gen.package_info = SimpleNamespace(
        module_collection=[module], source_hpp_files=[str(tmp_path / "Widget.hpp")]
    )
    gen.source_ns = SimpleNamespace(classes=lambda allow_empty=True: [])

    with caplog.at_level(logging.INFO):
        gen.log_unknown_classes()

    assert any("Unknown class Widget" in message for message in caplog.messages)
