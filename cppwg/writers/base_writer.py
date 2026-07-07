"""Base for wrapper code writers."""

from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from string import Template


class CppBaseWrapperWriter:
    """
    Base class for wrapper writers.

    Attributes
    ----------
    wrapper_templates : dict[str, Template]
        Templates with placeholders for generating wrapper code
    tidy_replacements : OrderedDict[str, str]
        A dictionary of replacements to use when tidying up C++ declarations
    """

    def __init__(self, wrapper_templates: dict[str, "Template"]) -> None:
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
