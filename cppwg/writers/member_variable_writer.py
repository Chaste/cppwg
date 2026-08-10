"""Wrapper code writer for C++ public data members."""

import logging
from typing import TYPE_CHECKING

from pygccxml import declarations

from cppwg.writers.base_writer import CppBaseWrapperWriter

if TYPE_CHECKING:
    from string import Template

    from pygccxml.declarations.class_declaration import class_t
    from pygccxml.declarations.variable import variable_t

    from cppwg.info.class_info import CppClassInfo


class CppClassMemberWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of public data member wrapper code.

    Emits a ``.def_readwrite`` (or ``.def_readonly`` for a const member) binding
    so a class's public data members are readable/writable from Python.

    Attributes
    ----------
    class_info : CppClassInfo
        The class information for the class owning the member
    variable_decl : pygccxml.declarations.variable_t
        The pygccxml declaration object for the member variable
    class_decl : pygccxml.declarations.class_t
        The class declaration for the class owning the member
    wrapper_templates : dict[str, Template]
        Templates with placeholders for generating wrapper code
    class_py_name : str | None
        The Python name of the class e.g. 'Foo_2_2'
    """

    def __init__(
        self,
        class_info: "CppClassInfo",
        template_idx: int,
        variable_decl: "variable_t",
        wrapper_templates: dict[str, "Template"],
    ) -> None:
        super().__init__(wrapper_templates)

        self.class_info: "CppClassInfo" = class_info
        self.variable_decl: "variable_t" = variable_decl
        self.class_decl: "class_t" = class_info.decls[template_idx]

        self.class_py_name = class_info.py_names[template_idx]
        if self.class_py_name is None:
            self.class_py_name = self.class_decl.name

    def exclude(self) -> bool:
        """
        Check if the member should be excluded from the wrapper code.

        Returns
        -------
        bool
            True if the member should be excluded, False otherwise.
        """
        logger = logging.getLogger()
        variable_decl = self.variable_decl

        # Skip members marked for exclusion in the config.
        excluded_variables = self.class_info.hierarchy_attribute_gather_flat(
            "excluded_variables"
        )
        if variable_decl.name in excluded_variables:
            return True

        # A bitfield member has no address, so &Class::field is ill-formed and it
        # cannot be bound with def_readwrite/def_readonly.
        if variable_decl.bits is not None:
            logger.debug(
                f"Skipping bitfield member {self.class_py_name}::{variable_decl.name}"
            )
            return True

        # A C-style array member (e.g. `double coords[3]`) cannot be bound: a
        # def_readwrite setter assigns to the member, but C arrays are not
        # assignable, and pybind11 has no type caster for a raw array, so both
        # def_readwrite and def_readonly fail to compile. is_const already sees
        # through the array, so this also covers const arrays bound read-only.
        if declarations.is_array(variable_decl.decl_type):
            logger.debug(
                f"Skipping array member {self.class_py_name}::{variable_decl.name}"
            )
            return True

        # Static data members need def_readwrite_static/def_readonly_static and,
        # for in-class-initialised static const members, an out-of-line definition
        # to take their address. Skip them for now (see issue #116 follow-up).
        if (
            variable_decl.type_qualifiers is not None
            and variable_decl.type_qualifiers.has_static
        ):
            logger.debug(
                f"Skipping static member {self.class_py_name}::{variable_decl.name}"
            )
            return True

        return False

    def generate_wrapper(self) -> str:
        """
        Generate the member variable wrapper code.

        Returns
        -------
        str
            The C++ wrapper code string, or "" if the member is excluded.
        """
        if self.exclude():
            return ""

        # A const member cannot be written from Python, so bind it read-only.
        if declarations.is_const(self.variable_decl.decl_type):
            access = "readonly"
        else:
            access = "readwrite"

        return self.wrapper_templates["class_member"].substitute(
            access=access,
            member_name=self.variable_decl.name,
            class_py_name=self.class_py_name,
        )
