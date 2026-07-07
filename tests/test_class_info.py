"""Unit tests for cppwg.info.class_info."""

from cppwg.info.class_info import CppClassInfo


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
