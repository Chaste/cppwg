"""Utility functions for the cppwg package."""

import ast
import os
import re
from numbers import Number
from typing import TYPE_CHECKING, Any

from cppwg.utils.constants import CPPWG_ALL_STRING, CPPWG_TRUE_STRINGS

if TYPE_CHECKING:
    from pygccxml.declarations.calldef_members import member_function_t
    from pygccxml.declarations.class_declaration import class_t


def ensure_trailing_newline(code: str) -> str:
    """
    Return `code` guaranteed to end with a newline (unless it is empty).

    Custom generators return raw C++ snippets with no trailing-newline
    guarantee (see call_generator_hook). When such a snippet is
    substituted into a wrapper template immediately ahead of another line, a
    missing newline glues the two together and can produce invalid C++ (e.g. a
    `#include` directive that no longer starts a line, or a closing `}` swallowed
    by a trailing `//` comment). Normalise the snippet here so callers can splice
    it safely regardless of how the generator formatted it.

    Parameters
    ----------
    code : str
        The generator-produced code snippet, possibly empty.

    Returns
    -------
    str
        The snippet guaranteed to end with a trailing newline, or "" unchanged.
    """
    if code and not code.endswith("\n"):
        return code + "\n"
    return code


def call_generator_hook(
    generator: Any, method_name: str, default: Any, *args: Any
) -> Any:
    """
    Call an optional custom-generator hook, returning ``default`` if absent.

    A custom generator need not subclass ``cppwg.templates.custom.Custom`` or
    implement every hook. A missing or non-callable hook - including the case of
    no generator at all (``generator`` is None) - yields ``default`` rather than
    raising, so partial or legacy generators keep working.

    Parameters
    ----------
    generator : Any
        The custom generator instance, or None.
    method_name : str
        The name of the hook to call, e.g. "get_class_cpp_def_code".
    default : Any
        The value to return when the hook is absent.
    *args : Any
        Positional arguments passed to the hook.

    Returns
    -------
    Any
        The hook's return value, or ``default`` if the hook is absent.
    """
    hook = getattr(generator, method_name, None)
    return hook(*args) if callable(hook) else default


def write_file_if_changed(filepath: str, content: str, overwrite: bool = False) -> bool:
    """
    Write content to filepath unless an identical file already exists.

    Skipping unchanged files leaves their modification time intact so that
    downstream build systems (e.g. make) do not needlessly recompile them.

    Parameters
    ----------
    filepath : str
        The path of the file to write.
    content : str
        The content to write to the file.
    overwrite : bool
        If True, always write the file even if its content is unchanged.

    Returns
    -------
    bool
        True if the file was written, False if it was skipped as unchanged.
    """
    if not overwrite and os.path.isfile(filepath):
        with open(filepath) as in_file:
            if in_file.read() == content:
                return False

    with open(filepath, "w") as out_file:
        out_file.write(content)

    return True


def convert_to_bool(value: Any) -> bool:
    """
    Convert value to a boolean.

    Parameters
    ----------
    value: Any
        The value to convert.

    Returns
    -------
    bool
        True if value is any of the true strings e.g. "YES", "ON"...
        False if value is a string but does not match any true string.
        bool(value) if value is not a string.
    """
    if isinstance(value, str):
        caps_string = value.strip().upper()
        if caps_string in CPPWG_TRUE_STRINGS:
            return True
        return False

    return bool(value)


def is_option_ALL(input_obj: Any) -> bool:
    """
    Check if the input is a string that matches the "ALL" indicator e.g. "CPPWG_ALL".

    Parameters
    ----------
    input_obj : Any
        The object to check

    Returns
    -------
    bool
        True if the input is a string that matches the "ALL" indicator
    """
    return isinstance(input_obj, str) and input_obj.upper() == CPPWG_ALL_STRING


# A single C++ identifier character, used to decide where identifier boundaries
# apply when matching type patterns.
_IDENTIFIER_CHAR = re.compile(r"[A-Za-z0-9_]")


def canonicalize_type_whitespace(type_string: str) -> str:
    """
    Collapse whitespace in a C++ type string to a canonical form.

    Whitespace is only significant where it separates two identifier characters
    (e.g. ``unsigned int``, ``const T``); everywhere else - around ``<``, ``,``,
    ``>``, ``*``, ``&``, ``::`` etc. - it is optional. This removes such optional
    whitespace and collapses the rest, so spellings that differ only in spacing
    become equal, e.g. ``TetrahedralMesh<3, 3>`` and ``TetrahedralMesh< 3,3 >``
    both become ``TetrahedralMesh<3,3>``.

    Parameters
    ----------
    type_string : str
        A C++ type string.

    Returns
    -------
    str
        The type string with insignificant whitespace removed.
    """
    collapsed = re.sub(r"\s+", " ", type_string.strip())
    # Drop a space unless it sits between two identifier characters.
    collapsed = re.sub(r" (?![A-Za-z0-9_])", "", collapsed)
    collapsed = re.sub(r"(?<![A-Za-z0-9_]) ", "", collapsed)
    return collapsed


def type_string_matches(type_string: str, pattern: str) -> bool:
    """
    Check whether a type pattern occurs in a C++ type string as a whole token.

    The match respects identifier boundaries so a pattern is not matched as part
    of a larger identifier: ``Node`` matches ``::Node<2> const &`` but not
    ``AbstractNode``. Patterns whose edges are not identifier characters (e.g.
    ending in ``*`` or ``&``) are matched literally at those edges. Whitespace
    that is not between two identifier characters is insignificant, so a pattern
    like ``TetrahedralMesh<3, 3>`` matches a type spelled ``TetrahedralMesh<3,3>``
    (and vice versa). This is used to decide whether a method/constructor
    argument or return type should be excluded from wrapping.

    Parameters
    ----------
    type_string : str
        The C++ type string to search (e.g. a pygccxml decl_string).
    pattern : str
        The type pattern to look for.

    Returns
    -------
    bool
        True if the pattern occurs in the type string as a whole token.
    """
    # A non-string pattern (e.g. a yaml scalar like `arg_type_excludes: 5`) is
    # not a valid type pattern; treat it as non-matching rather than crashing.
    if not isinstance(pattern, str) or not pattern:
        return False

    # Match on a whitespace-canonical form of both strings so that differences
    # in spacing around punctuation (which pygccxml and hand-written config may
    # spell differently) do not defeat the match.
    type_string = canonicalize_type_whitespace(type_string)
    pattern = canonicalize_type_whitespace(pattern)
    if not pattern:
        return False

    # Enforce an identifier boundary only on an edge whose pattern character is
    # itself an identifier character. A pattern ending in e.g. > / * / & should
    # still match when immediately followed by a letter, as in
    # "std::vector<int>const &".
    left = r"(?<![A-Za-z0-9_])" if _IDENTIFIER_CHAR.match(pattern[0]) else ""
    right = r"(?![A-Za-z0-9_])" if _IDENTIFIER_CHAR.match(pattern[-1]) else ""

    regex = left + re.escape(pattern) + right
    return re.search(regex, type_string) is not None


def find_classes_in_source(
    source: str,
    class_name: str = None,
    template_signature: str = None,
) -> list[tuple[str, str, str]]:
    """
    Find class definitions in a C++ source string.

    Parameters
    ----------
    source : str
        The source string
    class_name : str
        The class name to search for; if None, all classes are returned.
    template_signature : str
        The template signature to search for.

    Returns
    -------
    list[tuple[str, str, str]]
        A list of (struct/class, class_name, inheritance) tuples
    """
    regex = r"\b"

    if template_signature:
        signature = strip_source_whitespace(template_signature)
        regex += r"template\s*" + re.escape(signature) + r"\s*"

    regex += r"(class|struct)\s+"

    if class_name:
        name = strip_source_whitespace(class_name)
        regex += r"(" + re.escape(name) + r")"
    else:
        regex += r"(\w+)"

    regex += r"\s*(?::\s*([^{;]+))?\s*"  # Inheritance
    regex += r"\{"  # Start of class body

    classes = re.findall(regex, source)

    return classes


def find_classes_in_source_file(
    source_file_path: str,
    class_name: str = None,
    template_signature: str = None,
) -> list[tuple[str, str, str]]:
    """
    Find class definitions in a C++ source file.

    Parameters
    ----------
    source : str
        The path to the source file.
    class_name : str
        The class name to search for; if None, all classes are returned.
    template_signature : str
        The template signature to search for.

    Returns
    -------
    list[tuple[str, str, str]]
        A list of (struct/class, class_name, inheritance) tuples
    """
    source = read_source_file(
        source_file_path,
        strip_comments=True,
        strip_preprocessor=True,
        strip_whitespace=True,
    )

    classes = find_classes_in_source(
        source,
        class_name=class_name,
        template_signature=template_signature,
    )

    return classes


def split_template_args(arg_string: str) -> list[str]:
    """
    Split a template argument string on its top-level commas.

    Commas inside nested template arguments are not split on, so
    "PottsMesh<2>, 3" yields ["PottsMesh<2>", "3"] rather than three parts.

    Parameters
    ----------
    arg_string : str
        The contents between the outer angle brackets e.g. "2, 2".

    Returns
    -------
    list[str]
        The individual template arguments e.g. ["2", "2"].
    """
    args: list[str] = []
    depth = 0
    current = ""

    for char in arg_string:
        if char == "<":
            depth += 1
            current += char
        elif char == ">":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            args.append(current.strip())
            current = ""
        else:
            current += char

    if current.strip():
        args.append(current.strip())

    return args


# Match an integer literal carrying a C++ unsigned/long suffix, e.g. "2u", "3U",
# "2ull". Used to strip the suffix so a discovered argument matches the plain
# form ("2") used in config template_substitutions and the generated names.
_INTEGER_LITERAL_SUFFIX_RE = re.compile(r"\b(\d+)[uUlL]+\b")


def normalize_template_arg(arg: str) -> str:
    """
    Normalize a discovered template argument to a canonical form.

    An integer non-type template argument is rendered by pygccxml with its C++
    literal suffix (e.g. an ``unsigned`` argument of 2 becomes ``"2u"``), while
    config ``template_substitutions`` and the source-text scan use the plain
    form (``"2"``). Strip the suffix from any integer literal in the argument -
    including one nested in a type argument (``"PottsMesh<2u>"`` ->
    ``"PottsMesh<2>"``) - so both discovery paths and the generated class names
    agree. Non-integer text is left unchanged.

    Parameters
    ----------
    arg : str
        A single template argument e.g. ``"2u"`` or ``"PottsMesh<2u>"``.

    Returns
    -------
    str
        The argument with integer-literal suffixes stripped, e.g. ``"2"``.
    """
    return _INTEGER_LITERAL_SUFFIX_RE.sub(r"\1", arg.strip())


# Match an explicit template class instantiation e.g. "template class Foo<2, 2>;".
# The class name may be namespace-qualified; the argument list is captured
# non-greedily up to the "> ;" that ends the statement so nested "<...>" (e.g.
# Foo<Bar<2>>) is handled by backtracking to the final ">".
_TEMPLATE_INSTANTIATION_RE = re.compile(r"\btemplate\s+class\s+([\w:]+)\s*<(.+?)>\s*;")


def find_template_instantiations_in_source(
    source: str,
) -> dict[str, list[list[str]]]:
    """
    Find explicit template class instantiations in a C++ source string.

    Matches statements like `template class Foo<2, 2>;` and returns a map of
    (unqualified) class name to the list of template argument lists found, in
    source order. Reading the arguments from the source text (rather than from a
    parsed instantiation's name) makes them independent of how a particular
    CastXML version renders defaulted template arguments.

    Parameters
    ----------
    source : str
        The source string (typically already stripped of comments/whitespace).

    Returns
    -------
    dict[str, list[list[str]]]
        Map of base class name to discovered template arg lists,
        e.g. {"Foo": [["2"], ["3"]], "AbstractMesh": [["2", "2"]]}.
    """
    instantiation_map: dict[str, list[list[str]]] = {}

    for match in _TEMPLATE_INSTANTIATION_RE.finditer(source):
        # e.g. "foo::Bar" -> "Bar" to match the unqualified class info name
        name = match.group(1).split("::")[-1]

        args = [
            normalize_template_arg(arg) for arg in split_template_args(match.group(2))
        ]
        if not args:
            continue

        arg_lists = instantiation_map.setdefault(name, [])
        if args not in arg_lists:
            arg_lists.append(args)

    return instantiation_map


def find_template_instantiations_in_source_file(
    source_file_path: str,
) -> tuple[bool, dict[str, list[list[str]]]]:
    """
    Find explicit template instantiations in a C++ source file.

    Reads and strips the file once, returning (has_instantiations,
    instantiation_map):

    - has_instantiations is True if the file contains a `template class ...;`
      statement, directly or via a macro. Preprocessor lines are kept for this
      check so a macro that expands to an instantiation still flags its file
      (its instantiations cannot be found by the text scan, which does not
      expand macros, and are recovered from the parsed AST instead).
    - instantiation_map holds the instantiations found in the source text, with
      preprocessor lines stripped so that a macro *definition* of
      `template class ...;` is not mistaken for an instantiation. See
      find_template_instantiations_in_source.

    Parameters
    ----------
    source_file_path : str
        The path to the implementation file (typically .cpp).

    Returns
    -------
    tuple[bool, dict[str, list[list[str]]]]
        Whether the file contains an explicit instantiation, and the map of
        base class name to discovered template arg lists.
    """
    with open(source_file_path) as source_file:
        source = strip_source_comments("\n".join(line.rstrip() for line in source_file))

    if "template class" not in strip_source_whitespace(source):
        return False, {}

    scan_source = strip_source_whitespace(strip_source_preprocessor(source))
    return True, find_template_instantiations_in_source(scan_source)


def strip_outer_angle_brackets(signature: str) -> str:
    """
    Remove a single pair of enclosing angle brackets from a template signature.

    e.g. "<unsigned A, unsigned B>" -> "unsigned A, unsigned B". A signature with
    no surrounding brackets is returned unchanged (stripped of whitespace), so
    callers can pass either form.

    Parameters
    ----------
    signature : str
        A template signature, with or without its enclosing "<...>".

    Returns
    -------
    str
        The signature body without the outer angle brackets.
    """
    inner = signature.strip()
    if inner.startswith("<"):
        inner = inner[1:]
    if inner.endswith(">"):
        inner = inner[:-1]
    return inner


def parse_template_params(signature: str) -> list[str]:
    """
    Extract template parameter names from a template signature.

    Parameters
    ----------
    signature : str
        A template signature e.g. "<int A, int B = A>".

    Returns
    -------
    list[str]
        The parameter names e.g. ["A", "B"].
    """
    params: list[str] = []

    # Strip the outer angle brackets, then split on top-level commas only, so a
    # comma inside a nested template (e.g. a default like "std::map<int, int>")
    # does not split one parameter into two (see split_template_args).
    for part in split_template_args(strip_outer_angle_brackets(signature)):
        # e.g. "unsigned SPACE_DIM = 2" -> ["unsigned", "SPACE_DIM", "=", "2"].
        # split() (no argument) splits on runs of arbitrary whitespace and drops
        # empty tokens, so multiple spaces/tabs (e.g. "unsigned  DIM") do not
        # produce an empty token[1] and silently lose the parameter name.
        tokens = part.split()

        # Need at least a type and a name e.g. ["unsigned", "SPACE_DIM"]
        if len(tokens) < 2:
            continue

        # e.g. "SPACE_DIM" from ["unsigned", "SPACE_DIM", "=", "2"]
        param = tokens[1].split("=")[0].strip()
        if param:
            params.append(param)

    return params


def find_template_signature_in_source(source: str, class_name: str) -> str | None:
    """
    Find a class's template parameter list "<...>" in a C++ source string.

    Searches for the class's template declaration e.g.
    `template <unsigned ELEMENT_DIM, unsigned SPACE_DIM> class Foo` and returns
    the parameter list including its angle brackets e.g.
    "<unsigned ELEMENT_DIM, unsigned SPACE_DIM>".

    Parameters
    ----------
    source : str
        The source string (typically already stripped of comments/whitespace).
    class_name : str
        The class name to search for.

    Returns
    -------
    str | None
        The template parameter list (with angle brackets), or None if not found.
    """
    name = strip_source_whitespace(class_name)

    # A template parameter list may itself contain "<...>" (e.g. a default like
    # "std::map<int, int>"), so the closing ">" must be found by matching angle
    # brackets on depth - a [^>]* capture would stop at the first inner ">" and
    # miss the parameters. Scan each "template<" for its balanced "<...>" and
    # accept it only when the wanted class/struct name follows.
    for match in re.finditer(r"\btemplate\s*<", source):
        open_index = match.end() - 1  # index of the opening "<"
        depth = 0
        close_index = None
        for index in range(open_index, len(source)):
            if source[index] == "<":
                depth += 1
            elif source[index] == ">":
                depth -= 1
                if depth == 0:
                    close_index = index
                    break
        if close_index is None:
            continue

        tail = source[close_index + 1 :]
        if re.match(r"\s*(?:class|struct)\s+" + re.escape(name) + r"\b", tail):
            return source[open_index : close_index + 1]

    return None


def find_template_params_in_source(source: str, class_name: str) -> list[str]:
    """
    Find the template parameter names for a class in a C++ source string.

    e.g. ["ELEMENT_DIM", "SPACE_DIM"] from
    `template <unsigned ELEMENT_DIM, unsigned SPACE_DIM> class Foo`.

    Parameters
    ----------
    source : str
        The source string (typically already stripped of comments/whitespace).
    class_name : str
        The class name to search for.

    Returns
    -------
    list[str]
        The template parameter names, or an empty list if not found.
    """
    signature = find_template_signature_in_source(source, class_name)
    if signature is None:
        return []
    return parse_template_params(signature)


def template_has_default_param(source: str, class_name: str) -> bool:
    """
    Check whether a class's template declaration has a defaulted parameter.

    e.g. True for `template <unsigned A, unsigned B = A> class Foo`, because the
    second parameter has a default. Used to decide whether a CastXML version that
    drops defaulted trailing arguments can be trusted for this class.

    Parameters
    ----------
    source : str
        The source string (typically already stripped of comments/whitespace).
    class_name : str
        The class name to search for.

    Returns
    -------
    bool
        True if any template parameter has a default value.
    """
    signature = find_template_signature_in_source(source, class_name)
    if signature is None:
        return False

    inner = strip_outer_angle_brackets(signature)
    return any("=" in part for part in split_template_args(inner))


def find_member_function(
    class_decl: "class_t", method_name: str
) -> "member_function_t | None":
    """
    Find a member function on a class or any of its base classes.

    Searches the class itself and then its base classes (e.g. to find a what()
    method inherited from std::exception).

    Parameters
    ----------
    class_decl : pygccxml.declarations.class_t
        The class to search.
    method_name : str
        The name of the member function to find.

    Returns
    -------
    pygccxml.declarations.member_function_t | None
        The member function declaration, or None if not found.
    """
    method_decls = class_decl.member_functions(method_name, allow_empty=True)
    if method_decls:
        return method_decls[0]

    for hierarchy_info in class_decl.recursive_bases:
        # related_class is None for a base pygccxml could not resolve; skip it
        # rather than dereferencing None.
        base_class = hierarchy_info.related_class
        if base_class is None:
            continue
        method_decls = base_class.member_functions(method_name, allow_empty=True)
        if method_decls:
            return method_decls[0]

    return None


def read_source_file(
    source_file_path: str,
    strip_comments: bool = True,
    strip_preprocessor: bool = True,
    strip_whitespace: bool = True,
) -> str:
    """
    Read a C++ source file and strip it of non-essential elements.

    Parameters
    ----------
    source_file_path : str
        The path to the source file
    strip_comments : bool
        Strip comments from the source file
    strip_preprocessor : bool
        Strip preprocessor directive lines from the source file
    strip_whitespace : bool
        Strip whitespace from the source file

    Returns
    -------
    str
        The source file as a string
    """
    source = ""

    with open(source_file_path) as source_file:
        source = "\n".join(line.rstrip() for line in source_file)

    source = strip_source(
        source,
        strip_comments=strip_comments,
        strip_preprocessor=strip_preprocessor,
        strip_whitespace=strip_whitespace,
    )

    return source


def str_to_num(expr: str, integer: bool = False) -> Number:
    """
    Convert a literal string expression to a number e.g. "(-1)" to -1.

    Parameters
    ----------
    expr : str
        The string expression to convert

    Returns
    -------
    Number
        The converted number, or None if the conversion fails
    """
    try:
        result = ast.literal_eval(expr.strip())
        if isinstance(result, Number):
            if integer:
                return int(result)
            return float(result)
    except (SyntaxError, TypeError, ValueError):
        pass

    return None


def strip_source(
    source: str,
    strip_comments: bool = True,
    strip_preprocessor: bool = True,
    strip_whitespace: bool = True,
) -> str:
    """
    Strip elements from a C++ source string.

    Parameters
    ----------
    source_file_path : str
        The path to the source file
    strip_comments : bool
        Strip comments from the source file
    strip_preprocessor : bool
        Strip preprocessor directive lines from the source file
    strip_whitespace : bool
        Strip whitespace from the source file

    Returns
    -------
    str
        The stripped source string
    """
    if strip_comments:
        source = strip_source_comments(source)

    if strip_preprocessor:
        source = strip_source_preprocessor(source)

    if strip_whitespace:
        source = strip_source_whitespace(source)

    return source


def strip_source_comments(source: str) -> str:
    """
    Strip comments from a C++ source string.

    Parameters
    ----------
    source : str
        The source string

    Returns
    -------
    str
        The source string with comments stripped
    """
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", " ", source, flags=re.DOTALL)

    return source


def strip_source_preprocessor(source: str) -> str:
    """
    Strip preprocessor directives from a C++ source string.

    Parameters
    ----------
    source : str
        The source string

    Returns
    -------
    str
        The source string with preprocessor directives stripped
    """
    source = re.sub(r"#.*", "", source)

    return source


def strip_source_whitespace(source: str) -> str:
    """
    Strip newlines and non-essential whitespace from a C++ source string.

    Parameters
    ----------
    source : str
        The source string

    Returns
    -------
    str
        The source string with whitespace stripped
    """
    source = re.sub(r"[\r\n]", " ", source)
    source = re.sub(r"\b\s+|\s+\b", " ", source)
    source = re.sub(r"\B\s+|\s+\B", "", source)

    return source
