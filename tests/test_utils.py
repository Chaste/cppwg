"""Unit tests for cppwg.utils.utils."""

import os

import pytest

from cppwg.utils.utils import (
    find_template_instantiations_in_source,
    find_template_instantiations_in_source_file,
    find_template_params_in_source,
    normalize_template_arg,
    template_has_default_param,
    parse_template_params,
    split_template_args,
    type_string_matches,
    write_file_if_changed,
)


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
    src.write_text('#include "Node.hpp"\ntemplate class Node<2>;\ntemplate class Node<3>;\n')

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
        ("<unsigned ELEMENT_DIM, unsigned SPACE_DIM = ELEMENT_DIM>",
         ["ELEMENT_DIM", "SPACE_DIM"]),
        ("<int A, int B=A>", ["A", "B"]),
        ("<class MESH>", ["MESH"]),
        # Multiple spaces / tabs between tokens must not drop the parameter name
        ("<unsigned  ELEMENT_DIM,\tunsigned\tSPACE_DIM>",
         ["ELEMENT_DIM", "SPACE_DIM"]),
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
