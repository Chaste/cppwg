"""Unit tests for cppwg.parsers.source_parser."""

from types import SimpleNamespace

from cppwg.parsers import source_parser as sp_module
from cppwg.parsers.source_parser import CppSourceParser


def _parser():
    return CppSourceParser("/src", "/hdr.hpp", "/castxml", ["/inc"])


def test_parse_instantiations_skips_unparsable_file(monkeypatch):
    """A file that fails to parse is skipped with a warning, not fatal."""
    parser = _parser()
    monkeypatch.setattr(parser, "xml_generator_config", lambda: None)

    def boom(**kwargs):
        raise RuntimeError("castxml failed")

    monkeypatch.setattr(sp_module.parser, "parse", boom)

    assert parser.parse_instantiations(["/src/a.cpp"]) == {}


def test_parse_instantiations_collects_only_local_explicit_instantiations(
    monkeypatch, tmp_path
):
    """Only explicit instantiations defined in the scanned file are collected."""
    src = str(tmp_path / "Foo.cpp")

    no_location = SimpleNamespace(name="NoLoc", location=None)
    other_file = SimpleNamespace(
        name="Bar<2>", location=SimpleNamespace(file_name="/other.cpp")
    )
    not_instantiation = SimpleNamespace(
        name="Plain", location=SimpleNamespace(file_name=src)
    )
    instantiation = SimpleNamespace(
        name="Foo<2u>", location=SimpleNamespace(file_name=src)
    )
    duplicate = SimpleNamespace(
        name="Foo<2u>", location=SimpleNamespace(file_name=src)
    )
    namespace = SimpleNamespace(
        classes=lambda allow_empty=True: [
            no_location,
            other_file,
            not_instantiation,
            instantiation,
            duplicate,
        ]
    )

    parser = _parser()
    monkeypatch.setattr(parser, "xml_generator_config", lambda: None)
    monkeypatch.setattr(sp_module.parser, "parse", lambda **kwargs: ["decls"])
    monkeypatch.setattr(
        sp_module.declarations, "get_global_namespace", lambda decls: namespace
    )
    monkeypatch.setattr(
        sp_module.declarations.templates,
        "is_instantiation",
        lambda name: name.startswith("Foo<"),
    )
    monkeypatch.setattr(
        sp_module.declarations.templates, "split", lambda name: ("foo::Foo", ["2u"])
    )

    result = parser.parse_instantiations([src])

    # Unqualified base, suffix-normalized args, and the duplicate de-duplicated.
    assert result == {"Foo": [["2"]]}
