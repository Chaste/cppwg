"""Base for wrapper code writers."""

from collections import OrderedDict
from typing import Dict


class CppBaseWrapperWriter:
    """
    Base class for wrapper writers.

    Attributes
    ----------
    wrapper_templates : Dict[str, str]
        String templates with placeholders for generating wrapper code
    tidy_replacements : OrderedDict[str, str]
        A dictionary of replacements to use when tidying up C++ declarations
    """

    def __init__(self, wrapper_templates: Dict[str, str]) -> None:

        self.wrapper_templates = wrapper_templates
        self.tidy_replacements = OrderedDict(
            [
                (" ", ""),
                (",", "_"),
                ("<", "_lt_"),
                (">", "_gt_"),
                ("::", "_"),
                ("*", "Ptr"),
                ("&", "Ref"),
                ("-", "neg"),
            ]
        )

    def tidy_name(self, name: str) -> str:
        """
        Replace full C++ declarations with a simple version for use in typedefs.

        Example:
        "::foo::bar<double, 2>" -> "_foo_bar_lt_double_2_gt_"

        Parameters
        ----------
        name : str
            The C++ declaration to tidy up

        Returns
        -------
        str
            The tidied up C++ declaration
        """
        for key, value in self.tidy_replacements.items():
            name = name.replace(key, value)

        return name

    # TODO: This method is currently a placeholder. Consider implementing or removing.
    def default_arg_exclusion_criteria(self) -> bool:
        """
        Check if default arguments should be excluded from the wrapper code.

        Returns
        -------
        bool
            True if the default arguments should be excluded
        """
        return False
