"""Base for wrapper code writers."""

import re
from collections import OrderedDict
from typing import TYPE_CHECKING

from pygccxml.declarations import type_traits

from cppwg.utils import utils

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

    def render_default_args(
        self,
        arguments,
        exclude_default_args: bool,
        template_params: "list[str] | None" = None,
        template_args: "list[str] | None" = None,
        class_name: "str | None" = None,
        substitute_empty_init_list: bool = False,
    ) -> str:
        """
        Render the ``, py::arg("name")[ = value]`` fragment for a calldef.

        A ``py::arg("name")`` is always emitted for each argument (pybind11's
        keyword name). The C++ default *value* is appended only when the argument
        has one and ``exclude_default_args`` is False - so ``exclude_default_args``
        omits the default values, never the keyword names. Shared by the method,
        constructor and free-function writers so the three cannot diverge; they
        previously did - the free-function writer gated the whole loop, dropping
        the keyword names too when ``exclude_default_args`` was set.

        Parameters
        ----------
        arguments : iterable
            The calldef arguments, each with ``name``, ``default_value`` and
            ``decl_type``.
        exclude_default_args : bool
            When True, omit the ``= value`` while keeping the ``py::arg("name")``.
        template_params, template_args : list[str] | None
            Class template parameter names and their concrete arguments. When
            given, a default value referencing a parameter (e.g. ``Foo::DIM`` or
            ``DIM``) is substituted with its value - used by the method and
            constructor writers on templated classes; free functions pass None.
        class_name : str | None
            The class name used to qualify a template parameter in a default
            value (``Foo::DIM``). Required when template_params is given.
        substitute_empty_init_list : bool
            When True, a bare ``{}`` default is given its type, e.g.
            ``std::vector<Bar*> {}`` (constructor writer only).

        Returns
        -------
        str
            The fragment, e.g. ``, py::arg("i") = 1, py::arg("b")``.
        """
        fragment = ""
        for arg in arguments:
            fragment += f', py::arg("{arg.name}")'

            if arg.default_value is None or exclude_default_args:
                continue

            # Try to convert "(-1)" to "-1" etc.
            default_value = str(arg.default_value)
            value = utils.str_to_num(default_value, integer="int" in str(arg.decl_type))
            if value is not None:
                default_value = str(value)

            # Substitute class template parameters in the default value, e.g.
            # Foo::DIM_A -> 2 and <DIM_A> -> <2>.
            if template_params:
                for param, val in zip(template_params, template_args):
                    if param in default_value:
                        default_value = re.sub(
                            rf"\b{class_name}::{param}\b", str(val), default_value
                        )
                        default_value = re.sub(rf"\b{param}\b", f"{val}", default_value)

            # An empty initializer list needs its type, e.g.
            # `Foo(std::vector<Bar*> laminas = {})` generates
            # py::arg("laminas") = std::vector<Bar*> {}.
            if substitute_empty_init_list and default_value.replace(" ", "") == "{}":
                decl_type = type_traits.remove_const(arg.decl_type)
                default_value = decl_type.decl_string + " {}"

            fragment += f" = {default_value}"

        return fragment
