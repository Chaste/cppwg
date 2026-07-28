"""Unit tests for cppwg.utils.utils."""

import os

import pytest

from cppwg.utils.utils import (
    call_generator_hook,
    convert_to_bool,
    ensure_trailing_newline,
    find_classes_in_source,
    find_classes_in_source_file,
    find_member_function,
    find_template_instantiations_in_source,
    find_template_instantiations_in_source_file,
    find_template_params_in_source,
    find_template_signature_in_source,
    is_option_ALL,
    normalize_template_arg,
    parse_template_params,
    read_source_file,
    split_template_args,
    str_to_num,
    strip_source,
    template_has_default_param,
    type_string_matches,
    write_file_if_changed,
)


@pytest.mark.parametrize(
    "code, expected",
    [
        ("", ""),  # empty is left untouched (no spurious blank line)
        ("class X{};", "class X{};\n"),  # unterminated snippet gets a newline
        ('#include "foo.h"', '#include "foo.h"\n'),
        ("already\n", "already\n"),  # already terminated is unchanged
        ("two\nlines\n", "two\nlines\n"),
        ("// trailing comment", "// trailing comment\n"),
    ],
)
def test_ensure_trailing_newline(code, expected):
    """A non-empty snippet is guaranteed to end with a trailing newline."""
    assert ensure_trailing_newline(code) == expected


@pytest.mark.parametrize(
    "arg, expected",
    [
        ("2u", "2"),
        ("3U", "3"),
        ("2ul", "2"),
        ("2ull", "2"),
        ("2LL", "2"),
        ("2", "2"),  # already plain
        ("-1", "-1"),
        ("PottsMesh<2u>", "PottsMesh<2>"),  # nested integer argument
        ("Foo<2u, 3ul>", "Foo<2, 3>"),
        ("MESH", "MESH"),  # non-integer left unchanged
        ("Vec2u", "Vec2u"),  # identifier, not an integer literal
    ],
)
def test_normalize_template_arg(arg, expected):
    """Integer-literal suffixes are stripped; other text is left unchanged."""
    assert normalize_template_arg(arg) == expected


def test_find_template_instantiations_normalizes_suffixes():
    """Discovered args carrying an unsigned suffix are normalized to plain form."""
    instantiation_map = find_template_instantiations_in_source(
        "template class Foo<2u>;\ntemplate class Foo<3U>;\n"
    )

    assert instantiation_map == {"Foo": [["2"], ["3"]]}


def test_find_template_instantiations_in_source_file_plain(tmp_path):
    """A file with plain instantiations is a candidate; args come from the text."""
    src = tmp_path / "Node.cpp"
    src.write_text(
        '#include "Node.hpp"\ntemplate class Node<2>;\ntemplate class Node<3>;\n'
    )

    is_candidate, instantiation_map = find_template_instantiations_in_source_file(
        str(src)
    )

    assert is_candidate is True
    assert instantiation_map == {"Node": [["2"], ["3"]]}


def test_find_template_instantiations_in_source_file_macro(tmp_path):
    """A macro-declared instantiation flags the file but yields no text matches.

    Preprocessor lines are kept for the candidate check (so the file is picked
    up), but stripped for the scan (so the macro definition is not mistaken for
    an instantiation) - leaving the AST fallback to recover it.
    """
    src = tmp_path / "MacroMesh.cpp"
    src.write_text(
        '#include "MacroMesh.hpp"\n'
        "#define INST(E, S) template class MacroMesh<E, S>;\n"
        "INST(2, 2)\n"
        "INST(3, 3)\n"
    )

    is_candidate, instantiation_map = find_template_instantiations_in_source_file(
        str(src)
    )

    assert is_candidate is True
    assert instantiation_map == {}


def test_find_template_instantiations_in_source_file_none(tmp_path):
    """A file with no explicit instantiation is not a candidate."""
    src = tmp_path / "Plain.cpp"
    src.write_text('#include "Plain.hpp"\nint answer() { return 42; }\n')

    is_candidate, instantiation_map = find_template_instantiations_in_source_file(
        str(src)
    )

    assert is_candidate is False
    assert instantiation_map == {}


@pytest.mark.parametrize(
    "arg_string, expected",
    [
        ("2", ["2"]),
        ("2, 2", ["2", "2"]),
        ("PottsMesh<2>", ["PottsMesh<2>"]),
        # Commas inside nested templates are not split on
        ("PottsMesh<2>, 3", ["PottsMesh<2>", "3"]),
        ("Bar<2, 3>, 4", ["Bar<2, 3>", "4"]),
    ],
)
def test_split_template_args(arg_string, expected):
    """Template arg strings split on top-level commas only."""
    assert split_template_args(arg_string) == expected


@pytest.mark.parametrize(
    "source, expected",
    [
        # Multiple instantiations of one class, in source order
        (
            "template class Node<2>; template class Node<3>;",
            {"Node": [["2"], ["3"]]},
        ),
        # A defaulted second arg is kept as written (the whole point of reading
        # the source text rather than a CastXML-rendered instantiation name)
        (
            "template class AbstractMesh<2, 2>;",
            {"AbstractMesh": [["2", "2"]]},
        ),
        # Nested template argument
        (
            "template class MeshFactory<PottsMesh<2>>;",
            {"MeshFactory": [["PottsMesh<2>"]]},
        ),
        # Namespace-qualified name is reduced to the unqualified class name
        (
            "template class foo::Bar<2>;",
            {"Bar": [["2"]]},
        ),
        # Duplicate instantiations are de-duplicated
        (
            "template class Node<2>; template class Node<2>;",
            {"Node": [["2"]]},
        ),
        # No explicit instantiations
        ("class Plain {};", {}),
    ],
)
def test_find_template_instantiations_in_source(source, expected):
    """Explicit template instantiations are found with source-order args."""
    assert find_template_instantiations_in_source(source) == expected


@pytest.mark.parametrize(
    "signature, expected",
    [
        ("<unsigned DIM>", ["DIM"]),
        ("<unsigned ELEMENT_DIM, unsigned SPACE_DIM>", ["ELEMENT_DIM", "SPACE_DIM"]),
        (
            "<unsigned ELEMENT_DIM, unsigned SPACE_DIM = ELEMENT_DIM>",
            ["ELEMENT_DIM", "SPACE_DIM"],
        ),
        ("<int A, int B=A>", ["A", "B"]),
        ("<class MESH>", ["MESH"]),
        # Multiple spaces / tabs between tokens must not drop the parameter name
        ("<unsigned  ELEMENT_DIM,\tunsigned\tSPACE_DIM>", ["ELEMENT_DIM", "SPACE_DIM"]),
        # A comma inside a nested-template default must not split one parameter
        # into two (only top-level commas separate parameters).
        ("<class T = std::map<int, int>, unsigned DIM>", ["T", "DIM"]),
        # A malformed part with no name is skipped rather than crashing
        ("<T>", []),
    ],
)
def test_parse_template_params(signature, expected):
    """Template signatures parse into their parameter names."""
    assert parse_template_params(signature) == expected


@pytest.mark.parametrize(
    "source, class_name, expected",
    [
        ("template<unsigned SPACE_DIM> class Node {};", "Node", ["SPACE_DIM"]),
        (
            "template <unsigned ELEMENT_DIM, unsigned SPACE_DIM = ELEMENT_DIM>"
            " class AbstractMesh {};",
            "AbstractMesh",
            ["ELEMENT_DIM", "SPACE_DIM"],
        ),
        ("template<class MESH> class MeshFactory {};", "MeshFactory", ["MESH"]),
        # A forward declaration (no body) is matched too
        ("template<unsigned DIM> class Foo;", "Foo", ["DIM"]),
        # The right class is picked when several template classes share a file
        (
            "template<unsigned A> class Other {};"
            "template<unsigned B> class Target {};",
            "Target",
            ["B"],
        ),
        # A nested template in a default must not truncate the parameter list at
        # the first inner ">".
        ("template<class T = std::vector<int>> class Bar {};", "Bar", ["T"]),
        (
            "template<class T = std::map<int, int>, unsigned DIM> class Foo {};",
            "Foo",
            ["T", "DIM"],
        ),
        # An untemplated / absent class yields no params
        ("class Plain {};", "Plain", []),
    ],
)
def test_find_template_params_in_source(source, class_name, expected):
    """A class's template parameter names are found from its declaration."""
    assert find_template_params_in_source(source, class_name) == expected


@pytest.mark.parametrize(
    "source, class_name, expected",
    [
        ("template<unsigned DIM> class Foo {};", "Foo", False),
        ("template<unsigned A, unsigned B = A> class Foo {};", "Foo", True),
        ("template<unsigned A, unsigned B=A> class Foo {};", "Foo", True),
        # A comma in a nested-template default is not mistaken for a parameter.
        ("template<class T = std::map<int, int>> class Foo {};", "Foo", True),
        # Untemplated or absent class has no defaulted parameter.
        ("class Plain {};", "Plain", False),
        ("template<unsigned DIM> class Other {};", "Foo", False),
    ],
)
def test_template_has_default_param(source, class_name, expected):
    """A defaulted template parameter is detected from the class declaration."""
    assert template_has_default_param(source, class_name) is expected


@pytest.mark.parametrize(
    "type_string, pattern, expected",
    [
        # Whole-token identifier matches (not part of a larger identifier)
        ("::Node<2> const &", "Node", True),
        ("::AbstractNode<2> const &", "Node", False),
        ("Node", "Node", True),
        ("NodeIterator", "Node", False),
        ("MyNode", "Node", False),
        # Qualified / templated names
        ("::std::vector<Node> const &", "Node", True),
        ("boost::shared_ptr<Foo>", "boost::shared_ptr", True),
        ("myboost::shared_ptr<Foo>", "boost::shared_ptr", False),
        # Multi-token type names
        ("unsigned int const &", "unsigned int", True),
        ("unsigned integer", "unsigned int", False),
        # Patterns whose edge is not an identifier char still match
        ("::std::vector<int> const &", "std::vector<int>", True),
        ("int *", "int", True),
        # A pattern ending in a non-identifier char (>) still matches even when
        # immediately followed by an identifier char (no space before const).
        ("std::vector<int>const &", "std::vector<int>", True),
        # A pattern ending in an identifier char still requires a boundary.
        ("intx", "int", False),
        # Whitespace around punctuation is insignificant: the pattern and the
        # type string may differ in spacing inside/around the template args.
        ("TetrahedralMesh<3,3>", "TetrahedralMesh<3, 3>", True),
        ("TetrahedralMesh<3, 3>", "TetrahedralMesh<3,3>", True),
        ("VertexMesh<2, 2> const &", "VertexMesh< 2,2 >", True),
        ("TetrahedralMesh<2,2>", "TetrahedralMesh<3, 3>", False),
        # But whitespace between two identifiers is still significant.
        ("unsignedint", "unsigned int", False),
        # Empty pattern never matches
        ("int", "", False),
        # Non-string patterns (e.g. yaml scalars like `arg_type_excludes: 5`)
        # are non-matching rather than crashing on re.escape.
        ("5", 5, False),
        ("int", True, False),
    ],
)
def test_type_string_matches(type_string, pattern, expected):
    """Type patterns match as whole tokens, respecting identifier boundaries."""
    assert type_string_matches(type_string, pattern) is expected


def test_writes_when_file_missing(tmp_path):
    """A new file is created and reports that it was written."""
    filepath = os.path.join(tmp_path, "wrapper.cpp")

    wrote = write_file_if_changed(filepath, "content")

    assert wrote is True
    assert os.path.isfile(filepath)
    with open(filepath) as f:
        assert f.read() == "content"


def test_skips_when_content_unchanged(tmp_path):
    """An identical file is left untouched, preserving its mtime."""
    filepath = os.path.join(tmp_path, "wrapper.cpp")
    with open(filepath, "w") as f:
        f.write("content")

    # Backdate the mtime so any rewrite would be detectable
    old_time = os.path.getmtime(filepath) - 100
    os.utime(filepath, (old_time, old_time))
    old_time_ns = os.stat(filepath).st_mtime_ns

    wrote = write_file_if_changed(filepath, "content")

    assert wrote is False
    assert os.stat(filepath).st_mtime_ns == old_time_ns


def test_rewrites_when_content_changed(tmp_path):
    """A file with different content is rewritten."""
    filepath = os.path.join(tmp_path, "wrapper.cpp")
    with open(filepath, "w") as f:
        f.write("old content")

    wrote = write_file_if_changed(filepath, "new content")

    assert wrote is True
    with open(filepath) as f:
        assert f.read() == "new content"


def test_overwrite_forces_rewrite_when_unchanged(tmp_path):
    """With overwrite=True, an identical file is rewritten anyway."""
    filepath = os.path.join(tmp_path, "wrapper.cpp")
    with open(filepath, "w") as f:
        f.write("content")

    old_time = os.path.getmtime(filepath) - 100
    os.utime(filepath, (old_time, old_time))
    old_time_ns = os.stat(filepath).st_mtime_ns

    wrote = write_file_if_changed(filepath, "content", overwrite=True)

    assert wrote is True
    assert os.stat(filepath).st_mtime_ns != old_time_ns


def test_call_generator_hook():
    """An optional generator hook is called if present, else the default is used."""

    class PartialGenerator:
        def get_module_code(self):
            return "// code"

        def get_class_cpp_pre_code(self, class_py_name):
            return f"// {class_py_name}"

    gen = PartialGenerator()

    # Present hooks are called (with args forwarded).
    assert call_generator_hook(gen, "get_module_code", "") == "// code"
    assert call_generator_hook(gen, "get_class_cpp_pre_code", "", "Foo") == "// Foo"

    # A missing hook (generator does not subclass Custom / omits it) -> default.
    assert call_generator_hook(gen, "get_class_cpp_source_includes", []) == []
    assert call_generator_hook(gen, "get_class_cpp_def_code", "", "Foo") == ""

    # No generator at all -> default.
    assert call_generator_hook(None, "get_module_code", "DEFAULT") == "DEFAULT"

    # A non-callable attribute of that name -> default (treated as absent).
    class Weird:
        get_module_code = "not callable"

    assert call_generator_hook(Weird(), "get_module_code", "DEFAULT") == "DEFAULT"


@pytest.mark.parametrize(
    "value, expected",
    [
        ("YES", True),
        ("  on  ", True),  # stripped and upper-cased before matching
        ("no", False),
        ("anything", False),
        (1, True),  # non-string falls back to bool()
        (0, False),
        (None, False),
        ([], False),
    ],
)
def test_convert_to_bool(value, expected):
    assert convert_to_bool(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("CPPWG_ALL", True),
        ("cppwg_all", True),  # case-insensitive
        ("SOME", False),
        (5, False),  # non-string
    ],
)
def test_is_option_ALL(value, expected):
    assert is_option_ALL(value) is expected


def test_type_string_matches_whitespace_only_pattern():
    """A pattern that canonicalises to empty does not match anything."""
    assert type_string_matches("Node<2>", " ") is False


def test_find_classes_in_source_all_classes():
    source = "class Foo {}; struct Bar : public Base {};"
    found = find_classes_in_source(source)
    assert ("class", "Foo", "") in found
    assert ("struct", "Bar", "public Base ") in found


def test_find_classes_in_source_by_name_and_template():
    source = "template<unsigned DIM> class Foo {};"
    found = find_classes_in_source(
        source, class_name="Foo", template_signature="<unsigned DIM>"
    )
    assert len(found) == 1
    assert found[0][1] == "Foo"


def test_find_classes_in_source_file(tmp_path):
    src = tmp_path / "Foo.hpp"
    src.write_text("// a comment\n#include <x>\nclass Foo {};\n")
    found = find_classes_in_source_file(str(src), class_name="Foo")
    assert found[0][1] == "Foo"


def test_split_template_args_ignores_trailing_comma():
    """A trailing separator leaves no empty final argument."""
    assert split_template_args("2,") == ["2"]
    assert split_template_args("") == []


def test_parse_template_params_without_brackets_and_short_tokens():
    """A bare (unbracketed) list is handled, and tokens without a name skipped."""
    assert parse_template_params("unsigned A, class B") == ["A", "B"]
    # A part with fewer than two tokens contributes no parameter name.
    assert parse_template_params("<unsigned A, int>") == ["A"]


def test_find_template_signature_skips_unbalanced_template():
    """A `template<` with no closing bracket is skipped, not matched."""
    source = "template<unsigned A class Foo {"
    assert find_template_signature_in_source(source, "Foo") is None


@pytest.mark.parametrize(
    "expr, integer, expected",
    [
        ("(-1)", False, -1.0),
        ("(-1)", True, -1),
        ("2.5", False, 2.5),
        ("not_a_number", False, None),
        ("[1, 2]", False, None),  # literal_eval succeeds but is not a Number
    ],
)
def test_str_to_num(expr, integer, expected):
    assert str_to_num(expr, integer=integer) == expected


def test_read_source_file_strips(tmp_path):
    src = tmp_path / "Foo.cpp"
    src.write_text("// comment\n#include <x>\nclass  Foo  {  } ;\n")
    stripped = read_source_file(str(src))
    assert "//" not in stripped
    assert "#include" not in stripped
    assert "class Foo" in stripped


def test_strip_source_flags_are_independent():
    """Each strip step can be toggled off individually."""
    source = "// c\n#define X 1\nclass  Foo {};"
    # Nothing stripped: content preserved (only the object is returned as-is).
    assert strip_source(
        source,
        strip_comments=False,
        strip_preprocessor=False,
        strip_whitespace=False,
    ) == source
    # Only comments stripped.
    only_comments = strip_source(
        source,
        strip_comments=True,
        strip_preprocessor=False,
        strip_whitespace=False,
    )
    assert "// c" not in only_comments
    assert "#define" in only_comments


class _FakeMethod:
    def __init__(self, name):
        self.name = name


class _FakeBase:
    def __init__(self, related_class):
        self.related_class = related_class


class _FakeClass:
    def __init__(self, methods, bases=()):
        self._methods = methods
        self.recursive_bases = list(bases)

    def member_functions(self, name, allow_empty=True):
        return [m for m in self._methods if m.name == name]


def test_find_member_function_on_class():
    method = _FakeMethod("what")
    cls = _FakeClass([method])
    assert find_member_function(cls, "what") is method


def test_find_member_function_on_base():
    method = _FakeMethod("what")
    base = _FakeClass([method])
    derived = _FakeClass([], bases=[_FakeBase(None), _FakeBase(base)])
    # None-related base is skipped; the resolvable base provides the method.
    assert find_member_function(derived, "what") is method


def test_find_member_function_not_found():
    cls = _FakeClass([], bases=[_FakeBase(_FakeClass([]))])
    assert find_member_function(cls, "missing") is None


def test_find_template_instantiations_skips_empty_args():
    """An instantiation with no real arguments is skipped."""
    assert find_template_instantiations_in_source("template class Foo< >;") == {}


def test_parse_template_params_skips_empty_name_after_default():
    """A part whose name resolves to empty (e.g. "unsigned =2") is skipped."""
    assert parse_template_params("<unsigned =2>") == []
