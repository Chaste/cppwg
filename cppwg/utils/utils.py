"""Utility functions for the cppwg package."""

import ast
import os
import re
from numbers import Number
from typing import Any, List, Tuple

from cppwg.utils.constants import CPPWG_ALL_STRING, CPPWG_TRUE_STRINGS


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
        with open(filepath, "r") as in_file:
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


def find_classes_in_source(
    source: str,
    class_name: str = None,
    template_signature: str = None,
) -> List[Tuple[str, str, str]]:
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
    List[Tuple[str, str, str]]
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
) -> List[Tuple[str, str, str]]:
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
    List[Tuple[str, str, str]]
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

    with open(source_file_path, "r") as source_file:
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
