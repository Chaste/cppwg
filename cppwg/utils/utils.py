"""
Utility functions for the cppwg package
"""

from typing import Any


def is_option_ALL(input_obj: Any, option_ALL_string: str = "CPPWG_ALL") -> bool:
    """
    Check if the input is a string that matches the "ALL" indicator e.g. "CPPWG_ALL"

    Parameters
    ----------
    input_obj : Any
        The object to check
    option_ALL_string : str
        The string to check against

    Returns
    -------
    bool
        True if the input is a string that matches the "ALL" indicator
    """
    return isinstance(input_obj, str) and input_obj.upper() == option_ALL_string


def substitute_bool_for_string(input_dict: dict[Any, Any], key: Any) -> None:
    """
    Substitute a string in the input dictionary with a boolean value if the
    string is a boolean indicator e.g. "ON", "OFF", "YES", "NO", "TRUE", "FALSE"

    Parameters
    ----------
    input_dict : dict[Any, Any]
        The input dictionary
    key : Any
        The key to check
    """

    if not isinstance(input_dict[key], str):
        return

    caps_string = input_dict[key].strip().upper()

    if caps_string in ["OFF", "NO", "N", "FALSE", "F"]:
        input_dict[key] = False

    elif caps_string in ["ON", "YES", "Y", "TRUE", "T"]:
        input_dict[key] = True
