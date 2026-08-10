"""Wrapper code writer for C++ classes."""

import logging
import os
from typing import TYPE_CHECKING

from pygccxml.declarations import type_traits_classes
from pygccxml.declarations.matchers import access_type_matcher_t

from cppwg.utils.constants import (
    CPPWG_CLASS_OVERRIDE_SUFFIX,
    CPPWG_EXT,
    CPPWG_HEADER_COLLECTION_FILENAME,
)
from cppwg.utils.utils import (
    call_generator_hook,
    canonicalize_type_whitespace,
    ensure_trailing_newline,
    type_string_matches,
    write_file_if_changed,
)
from cppwg.writers.base_writer import CppBaseWrapperWriter
from cppwg.writers.constructor_writer import CppConstructorWrapperWriter
from cppwg.writers.member_variable_writer import CppClassMemberWrapperWriter
from cppwg.writers.method_writer import CppMethodWrapperWriter

if TYPE_CHECKING:
    from string import Template

    from pygccxml.declarations.calldef_members import member_function_t
    from pygccxml.declarations.class_declaration import class_t

    from cppwg.info.class_info import CppClassInfo


class CppClassWrapperWriter(CppBaseWrapperWriter):
    """
    Writer to generate wrapper code for C++ classes.

    Attributes
    ----------
    class_info : CppClassInfo
        The class information
    wrapper_templates : dict[str, Template]
        Templates with placeholders for generating wrapper code
    module_classes : dict[pygccxml.declarations.class_t, str]
        A dictionary of decls and names for all classes in the module
    package_classes : set[pygccxml.declarations.class_t]
        Decls for every class wrapped anywhere in the package (all modules).
        Used to detect base classes wrapped in another module of this package.
    package_class_infos : dict[pygccxml.declarations.class_t, CppClassInfo]
        Maps each wrapped decl to its class_info. Used by the inherited-override
        skip to consult a base class's excluded_methods.
    overwrite : bool
        Force rewrite of the class wrapper files, even if unchanged
    hpp_string : str
        The hpp wrapper code
    cpp_string : str
        The cpp wrapper code
    """

    def __init__(
        self,
        class_info: "CppClassInfo",
        wrapper_templates: dict[str, "Template"],
        module_classes: dict["class_t", str],
        package_classes: set["class_t"] = None,
        overwrite: bool = False,
        package_class_infos: dict["class_t", "CppClassInfo"] = None,
    ) -> None:
        logger = logging.getLogger()

        super().__init__(wrapper_templates)

        self.class_info = class_info

        if len(self.class_info.cpp_names) != len(self.class_info.py_names):
            logger.error("C++ and Python class name lists should be the same length")
            raise AssertionError()

        self.module_classes = module_classes
        self.package_classes = package_classes if package_classes is not None else set()
        self.package_class_infos = (
            package_class_infos if package_class_infos is not None else {}
        )

        self.overwrite = overwrite

        self.hpp_string: str = ""
        self.cpp_string: str = ""

        # Type-caster headers to include in this class's wrapper .cpp, detected
        # from the generated registration text in write(). Empty until then.
        self.typecaster_includes: list[str] = []

    def prefix_block(self) -> str:
        """
        Return the prefix text block for the top of a wrapper file.

        Returns
        -------
        str
            The prefix text followed by a newline, or an empty string.
        """
        prefix_text = self.class_info.hierarchy_attribute("prefix_text")
        return f"{prefix_text}\n" if prefix_text else ""

    @staticmethod
    def _format_include(entry: str) -> str:
        """
        Format one `#include` line for a header entry, or "" to skip it.

        An angle-bracket entry (e.g. `<string>` or `<petsc/caster.h>`) becomes
        `#include <...>`; anything else becomes a quoted `#include "..."`. A
        non-string or empty entry (e.g. a mis-typed yaml scalar) is skipped. Used
        for both `source_includes` and auto-detected type-caster headers so the
        two accept the same `<...>` / `"..."` spellings.

        Parameters
        ----------
        entry : str
            A header entry, e.g. `Foo.hpp` or `<string>`.

        Returns
        -------
        str
            The formatted include line (with trailing newline), or "".
        """
        if not isinstance(entry, str) or not entry:
            return ""
        if entry.startswith("<"):
            # e.g. #include <string>
            return f"#include {entry}\n"
        # e.g. #include "Foo.hpp"
        return f'#include "{entry}"\n'

    def includes_block(self) -> str:
        """
        Return the `#include` block for a class wrapper cpp file.

        Returns
        -------
        str
            The include directives, one per line.
        """
        # Build an order-preserving, de-duplicated list of include lines. A
        # header could legitimately reach this block from more than one source
        # e.g. a type-caster header that is auto-detected *and* listed
        # manually under source_includes.
        seen: set[str] = set()
        lines: list[str] = []

        def add(line: str) -> None:
            if line and line not in seen:
                seen.add(line)
                lines.append(line)

        common_include = self.class_info.hierarchy_attribute("common_include_file")
        if common_include:
            add(f'#include "{CPPWG_HEADER_COLLECTION_FILENAME}"\n')

        # Auto-detected type-caster headers, added to the wrappers whose
        # signatures use the caster's types. A caster header may be spelled with
        # angle brackets (e.g. `<petsc/caster.h>`) or quoted, like source_includes.
        for header in self.typecaster_includes:
            add(self._format_include(header))

        # Headers a custom generator's emitted code needs. A generator can name
        # types in its get_class_cpp_def_code() output that never appear in the
        # parsed signatures (e.g. GetAreaIn<SquareMetres>), so cppwg cannot
        # auto-detect them; it declares them via the optional get_class_cpp_source_includes()
        # hook. These are emitted before the common-include early return: they may
        # be <...> system headers or otherwise absent from the wrapper header
        # collection, so the header collection alone would not pull them in.
        for header in call_generator_hook(
            self.class_info.custom_generator_instance,
            "get_class_cpp_source_includes",
            [],
        ):
            add(self._format_include(header))

        if common_include:
            return "".join(lines)

        # Auto-resolved headers for the project types this class's wrapped
        # signatures use (empty unless auto_includes is enabled). Emitted with the
        # class's other includes; the dedup above drops any that a caster or a
        # manual source_includes entry already covers.
        for header in self.class_info.auto_include_headers:
            add(self._format_include(header))

        # Non-common: the class's explicit source_includes, then its own header.
        # Caster headers already lead the block, so a caster duplicated here is
        # skipped rather than emitted a second time.
        for source_include in self.class_info.hierarchy_attribute_gather_flat(
            "source_includes"
        ):
            add(self._format_include(source_include))

        source_file = self.class_info.source_file
        if not source_file:
            source_file = os.path.basename(self.class_info.decls[0].location.file_name)
        add(f'#include "{source_file}"\n')

        return "".join(lines)

    def smart_ptr_handle(self) -> str:
        """
        Return the smart pointer holder declaration, or an empty string.

        Returns
        -------
        str
            e.g. "PYBIND11_DECLARE_HOLDER_TYPE(T, boost::shared_ptr<T>)".
        """
        smart_ptr_type = self.class_info.hierarchy_attribute("smart_ptr_type")
        if not smart_ptr_type:
            return ""
        return self.wrapper_templates["smart_pointer_holder"].substitute(
            holder=smart_ptr_type
        )

    def prefix_code(self) -> str:
        """Return any custom prefix code lines for the class."""
        return "".join(f"{code_line}\n" for code_line in self.class_info.prefix_code)

    def suffix_code(self) -> str:
        """Return any custom suffix code lines for the class."""
        return "".join(f"{code_line}\n" for code_line in self.class_info.suffix_code)

    def virtual_overrides(
        self, template_idx: int
    ) -> tuple[str, str, list["member_function_t"]]:
        """
        Build the virtual "trampoline" override block for the class.

        Identify any methods needing overrides (i.e. any that are virtual in the
        current class or in a base class), and build the trampoline override
        class that forwards them to Python.

        Parameters
        ----------
        template_idx : int
            The index of the template in the class info

        Returns
        -------
        tuple[str, str, list[pygccxml.declarations.member_function_t]]
            The return-type typedef block, the override class block (empty if
            the class has no virtual methods), and the list of methods needing
            an override.
        """
        methods_needing_override: list["member_function_t"] = []
        return_types: list[str] = []  # e.g. ["void", "unsigned int", "::Bar<2> *"]

        # Collect all virtual methods and their return types
        class_decl = self.class_info.decls[template_idx]

        for member_function in class_decl.member_functions(allow_empty=True):
            is_pure_virtual = member_function.virtuality == "pure virtual"
            is_virtual = member_function.virtuality == "virtual"
            if is_pure_virtual or is_virtual:
                methods_needing_override.append(member_function)
                return_types.append(member_function.return_type.decl_string)

        # Add typedefs for return types with special characters
        # e.g. typedef ::Bar<2> * _Bar_lt_2_gt_Ptr;
        return_typedefs = ""
        for return_type in return_types:
            if return_type != self.tidy_name(return_type):
                return_typedefs += "typedef {class_cpp_name} {tidy_name};\n".format(
                    class_cpp_name=return_type,
                    tidy_name=self.tidy_name(return_type),
                )

        # Override virtual methods
        override_class = ""
        if methods_needing_override:
            # Add virtual override class, e.g.:
            #   class Foo_Overrides : public Foo {
            #       public:
            #       using Foo::Foo;
            class_py_name = self.class_info.py_names[template_idx]
            override_class += self.wrapper_templates[
                "class_virtual_override_header"
            ].substitute(
                class_py_name=class_py_name,
                class_base_name=self.class_info.name,
            )

            # Override each method, e.g.:
            #   void bar(double d) const override {
            #       PYBIND11_OVERRIDE_PURE(
            #           bar,
            #           Foo_2_2,
            #           bar,
            #           d);
            #   }
            for method in methods_needing_override:
                method_writer = CppMethodWrapperWriter(
                    self.class_info,
                    template_idx,
                    method,
                    self.wrapper_templates,
                )
                override_class += method_writer.generate_virtual_override_wrapper()

            override_class += "};\n\n"

        return return_typedefs, override_class, methods_needing_override

    def bases_block(self, class_decl: "class_t") -> str:
        """
        Return the base-class list appended to the ``py::class_`` declaration.

        Cross-module inheritance is opted into per module via `imports`. When
        set, a base class that is not wrapped in this module may still be
        referenced, but only if it is known to be registered elsewhere: either
        it is wrapped in another module of this package, or the user has listed
        it under `external_bases` (for bases wrapped in an imported package).
        This avoids emitting unregistered bases (e.g. framework/utility bases),
        which would fail at import.

        Parameters
        ----------
        class_decl : pygccxml.declarations.class_t
            The class declaration whose bases to inspect.

        Returns
        -------
        str
            e.g. ", AbstractFoo, InterfaceFoo".
        """
        bases = ""

        allow_external_bases = bool(self.class_info.hierarchy_attribute("imports"))
        external_bases = self.class_info.hierarchy_attribute("external_bases")
        if isinstance(external_bases, str):
            # A scalar (e.g. `external_bases: AbstractFoo`) is a single base
            # name; wrap it so the membership test below is exact rather than a
            # substring match (e.g. "Foo" in "AbstractFoo").
            external_bases = [external_bases]
        elif not isinstance(external_bases, (list, tuple, set)):
            # Unset (None) or any other mis-typed scalar -> no external bases.
            external_bases = []
        # Compare on unqualified names: the base's pygccxml name is unqualified,
        # so accept either a qualified or unqualified config entry (e.g. both
        # "foo::AbstractBar" and "AbstractBar" match a base named AbstractBar).
        external_bases = {str(name).split("::")[-1] for name in external_bases}

        for base in class_decl.bases:  # type(base) -> hierarchy_info_t
            # Check that the base class is not private
            if base.access_type == "private":
                continue

            related_class = base.related_class

            if related_class in self.module_classes:
                # Base class is wrapped in this module: refer to it by its
                # Python wrapper name.
                bases += f", {self.module_classes[related_class]}"

            elif (
                allow_external_bases
                and related_class is not None
                and (
                    related_class in self.package_classes
                    or related_class.name.split("<", 1)[0] in external_bases
                )
            ):
                # Base class is wrapped in another module - either elsewhere in
                # this package, or in an imported package (listed under
                # `external_bases`). Refer to it by its C++ type so that pybind11
                # links the inheritance at runtime. The module that registers the
                # base must be listed under `imports` so that it is imported
                # before this class is registered.
                bases += f", {related_class.decl_string}"

        return bases

    def build_hpp(self, register_py_names: list[str]) -> str:
        """
        Build the class wrapper hpp file contents.

        One hpp is emitted per class, forward-declaring the register function for
        every instantiation that is written.

        Parameters
        ----------
        register_py_names : list[str]
            The Python names of the instantiations that have a register function,
            e.g. ["Foo_2_2", "Foo_3_3"].

        Returns
        -------
        str
            The hpp wrapper code.
        """
        decl_template = self.wrapper_templates["class_hpp_register_declaration"]
        register_declarations = "".join(
            decl_template.substitute(class_py_name=class_py_name)
            for class_py_name in register_py_names
        )
        return self.wrapper_templates["class_hpp"].substitute(
            prefix_text=self.prefix_block(),
            class_hpp_name=self.class_info.py_name_base(),
            register_declarations=register_declarations,
        )

    def build_cpp_header(
        self, class_typedefs: str = "", return_typedefs: str = ""
    ) -> str:
        """
        Build the shared preamble of the class wrapper cpp file.

        Emitted once per class (not per instantiation): the includes, the smart
        pointer holder declaration, class-level prefix code, the per-instantiation
        alias typedefs, and the deduplicated trampoline return typedefs.

        Parameters
        ----------
        class_typedefs : str
            The alias typedefs (typedef <cpp> <py>;) for every instantiation in
            the file, emitted ahead of the registration blocks so any block can
            refer to any instantiation by its alias.
        return_typedefs : str
            The trampoline return typedefs, deduplicated across instantiations.

        Returns
        -------
        str
            The cpp preamble.
        """
        return self.wrapper_templates["class_cpp_header"].substitute(
            prefix_text=self.prefix_block(),
            includes=self.includes_block(),
            class_hpp_name=self.class_info.py_name_base(),
            smart_ptr_handle=self.smart_ptr_handle(),
            prefix_code=self.prefix_code(),
            class_typedefs=class_typedefs,
            return_typedefs=return_typedefs,
        )

    def _overrides_wrapped_base_virtual(
        self, class_decl: "class_t", method_decl: "member_function_t"
    ) -> bool:
        """
        Return True if a method overrides a virtual wrapped on a wrapped base.

        The method qualifies if it is virtual or pure virtual and some base class,
        wrapped in this package and not class-excluded, declares its own member
        function of the same name, argument types and const-ness that is itself
        virtual (the return type is intentionally not compared, so a
        covariant-return override still matches), and that base does not itself
        exclude the method from wrapping - by name, return type or arg type, the
        same rules as CppMethodWrapperWriter.method_is_excluded (otherwise the base
        emits no binding, so this override is the only one). The base must also be
        reachable from
        the derived py::class_ via an emitted pybind11 base link: a same-module
        base is always linked, but a base wrapped in another module of the package
        is only linked when cross-module inheritance is enabled (`imports` set) -
        see bases_block. Without that link the base's binding is not inherited, so
        the override would become unreachable if skipped. This is the per-method
        test used by _is_inherited_override; it does not consider sibling
        overloads.

        Parameters
        ----------
        class_decl : pygccxml.declarations.class_t
            The class declaration owning the method.
        method_decl : pygccxml.declarations.member_function_t
            The candidate member function.

        Returns
        -------
        bool
            True if the method overrides a wrapped base virtual.
        """
        if method_decl.virtuality not in ("virtual", "pure virtual"):
            return False

        # Cross-module inheritance is only linked into the derived py::class_ when
        # the module opts in via `imports` (see bases_block). Without it, a base
        # wrapped in another module contributes no inherited binding, so an
        # override of it here is the sole binding and must not be skipped.
        allow_external_bases = bool(self.class_info.hierarchy_attribute("imports"))

        name = method_decl.name
        arg_types = [
            canonicalize_type_whitespace(t.decl_string)
            for t in method_decl.argument_types
        ]

        for hierarchy_info in class_decl.recursive_bases:
            base_decl = hierarchy_info.related_class
            # Skip bases pygccxml could not resolve, and bases not wrapped in this
            # package (an unwrapped base provides no binding to inherit).
            if base_decl is None or base_decl not in self.package_classes:
                continue
            # A base wrapped in another module only provides an inherited binding
            # when its pybind base link is emitted (imports enabled). A same-module
            # base (in module_classes) is always linked.
            if base_decl not in self.module_classes and not allow_external_bases:
                continue

            for base_method in base_decl.member_functions(name, allow_empty=True):
                # Only public methods are bound (build_class_register filters on
                # public access), so a protected/private base virtual is not
                # wrapped on the base and cannot make this override redundant.
                if base_method.access_type != "public":
                    continue
                if base_method.virtuality not in ("virtual", "pure virtual"):
                    continue
                if base_method.has_const != method_decl.has_const:
                    continue
                base_arg_types = [
                    canonicalize_type_whitespace(t.decl_string)
                    for t in base_method.argument_types
                ]
                if base_arg_types != arg_types:
                    continue
                # The base declares a matching virtual. Keep the override only if
                # the base does not actually wrap it: a base method excluded from
                # wrapping (by name, return type or arg type - the same rules as
                # CppMethodWrapperWriter) emits no binding, so this override is the
                # sole binding and must not be skipped.
                base_info = self.package_class_infos.get(base_decl)
                if base_info is not None and CppMethodWrapperWriter.method_is_excluded(
                    base_info, base_decl, base_method
                ):
                    continue
                return True

        return False

    def _is_inherited_override(
        self, class_decl: "class_t", method_decl: "member_function_t"
    ) -> bool:
        """
        Return True if a method's binding is a redundant inherited override.

        With ``exclude_inherited_overrides`` set, a method that overrides a virtual
        method already wrapped on a wrapped base class need not be bound again: pybind11
        inheritance exposes the base binding and virtual dispatch routes the call
        to this override. Only the ``.def`` is skipped - the virtual trampoline
        (see virtual_overrides) is unaffected, so Python subclasses can still
        override the method.

        The method must itself override a wrapped base virtual
        (_overrides_wrapped_base_virtual) AND *every other public overload of the
        same name that will actually be wrapped* must too. This overload guard
        matters because pybind11 resolves overloads by name: a derived binding of
        a name shadows the inherited base binding for that name. So if the class
        still binds some other overload of this name, that surviving binding would
        hide the base's binding of this one - making it uncallable from Python.
        Skipping is safe only when the class binds none of that name and thus
        inherits the base's full overload set. A sibling overload that is itself
        excluded from wrapping (excluded_methods / return_type_excludes /
        arg_type_excludes, i.e. CppMethodWrapperWriter.method_is_excluded) emits
        no binding, so it cannot shadow and does not block skipping.

        Parameters
        ----------
        class_decl : pygccxml.declarations.class_t
            The class declaration owning the method.
        method_decl : pygccxml.declarations.member_function_t
            The candidate member function.

        Returns
        -------
        bool
            True if the binding should be skipped as a redundant override.
        """
        if not self.class_info.hierarchy_attribute("exclude_inherited_overrides"):
            return False

        if not self._overrides_wrapped_base_virtual(class_decl, method_decl):
            return False

        # Overload-shadowing guard: skip only if no other public overload of the
        # same name survives as a binding (i.e. every same-name overload is also a
        # skippable override). Otherwise the surviving overload shadows the base.
        query = access_type_matcher_t("public")
        for sibling in class_decl.member_functions(
            method_decl.name, function=query, allow_empty=True
        ):
            if sibling is method_decl:
                continue
            # A sibling that will not be wrapped (excluded by name/type) emits no
            # binding, so it cannot shadow the base and does not force keeping.
            if CppMethodWrapperWriter.method_is_excluded(
                self.class_info, class_decl, sibling
            ):
                continue
            if not self._overrides_wrapped_base_virtual(class_decl, sibling):
                return False

        return True

    def build_class_register(self, template_idx: int) -> tuple[str, str]:
        """
        Build the registration block for one template instantiation.

        Parameters
        ----------
        template_idx : int
            The index of the template instantiation in the class info.

        Returns
        -------
        tuple[str, str]
            The registration block and its trampoline return typedefs (the
            latter are hoisted into the shared preamble and deduplicated).
        """
        class_cpp_name = self.class_info.cpp_names[template_idx]
        class_py_name = self.class_info.py_names[template_idx]
        class_decl = self.class_info.decls[template_idx]
        generator = self.class_info.custom_generator_instance

        # Find and define virtual function "trampoline" overrides
        (
            return_typedefs,
            override_class,
            methods_needing_override,
        ) = self.virtual_overrides(template_idx)

        # Add the trampoline override class to the class definition if needed
        # e.g. py::class_<Foo, Foo_Overrides>(m, "Foo")
        overrides_string = ""
        if methods_needing_override:
            overrides_string = f", {class_py_name}{CPPWG_CLASS_OVERRIDE_SUFFIX}"

        # Add smart pointer support to the wrapper class definition if needed
        # e.g. py::class_<Foo, boost::shared_ptr<Foo>>(m, "Foo")
        ptr_support = ""
        smart_ptr_type = self.class_info.hierarchy_attribute("smart_ptr_type")
        if smart_ptr_type:
            ptr_support = f", {smart_ptr_type}<{class_py_name}>"

        # Add public constructors
        query = access_type_matcher_t("public")
        constructors = "".join(
            CppConstructorWrapperWriter(
                self.class_info,
                template_idx,
                constructor,
                self.wrapper_templates,
            ).generate_wrapper()
            for constructor in class_decl.constructors(function=query, allow_empty=True)
        )

        # Add public member functions. A method that redundantly overrides a
        # virtual already wrapped on a wrapped base class is skipped when
        # exclude_inherited_overrides is set (its trampoline, built separately in
        # virtual_overrides, is kept).
        methods = "".join(
            CppMethodWrapperWriter(
                self.class_info,
                template_idx,
                member_function,
                self.wrapper_templates,
            ).generate_wrapper()
            for member_function in class_decl.member_functions(
                function=query, allow_empty=True
            )
            if not self._is_inherited_override(class_decl, member_function)
        )

        # Add public data members, bound with def_readwrite (or def_readonly for
        # const members). The writer skips members that cannot be bound: static,
        # bitfield, array, reference, and (from the recursive query) nested-class
        # members.
        members = "".join(
            CppClassMemberWrapperWriter(
                self.class_info,
                template_idx,
                variable,
                self.wrapper_templates,
            ).generate_wrapper()
            for variable in class_decl.variables(function=query, allow_empty=True)
        )

        block = self.wrapper_templates["class_cpp_register"].substitute(
            generator_pre_code=call_generator_hook(
                generator, "get_class_cpp_pre_code", "", class_py_name
            ),
            class_py_name=class_py_name,
            class_cpp_name=class_cpp_name,
            override_class=override_class,
            overrides_string=overrides_string,
            ptr_support=ptr_support,
            bases=self.bases_block(class_decl),
            constructors=constructors,
            methods=methods,
            members=members,
            # Normalise the generator snippet to end with a newline: it is spliced
            # into the .def() chain ahead of suffix_code and the closing `;`, so a
            # missing newline (or a trailing // comment) could swallow the
            # statement terminator. See ensure_trailing_newline.
            generator_def_code=ensure_trailing_newline(
                call_generator_hook(
                    generator, "get_class_cpp_def_code", "", class_py_name
                )
            ),
            suffix_code=self.suffix_code(),
        )
        return block, return_typedefs

    def build_struct_enum_register(self, template_idx: int) -> str:
        """
        Build the registration block for a struct-enum instantiation.

        Handles a struct that wraps a single nested enum, for example::

            struct Foo {
              enum Value {A, B, C};
            };

        Parameters
        ----------
        template_idx : int
            The index of the template instantiation in the class info.

        Returns
        -------
        str
            The registration block.
        """
        class_cpp_name = self.class_info.cpp_names[template_idx]
        class_py_name = self.class_info.py_names[template_idx]
        class_decl = self.class_info.decls[template_idx]
        generator = self.class_info.custom_generator_instance

        enum_decl = class_decl.enumerations(allow_empty=True)[0]
        # Refer to the class through the wrapper alias (class_py_name), which is
        # typedef'd to the C++ type, so the registration function name matches
        # the hpp declaration and the module's register_..._class call even when
        # class_py_name differs from the C++ decl name (templates, name overrides).
        enum_values = "".join(
            '        .value("{val}", {class_py_name}::{enum_name}::{val})\n'.format(
                val=value[0],
                class_py_name=class_py_name,
                enum_name=enum_decl.name,
            )
            for value in enum_decl.values
        )

        return self.wrapper_templates["struct_enum_register"].substitute(
            generator_pre_code=call_generator_hook(
                generator, "get_class_cpp_pre_code", "", class_py_name
            ),
            class_py_name=class_py_name,
            class_cpp_name=class_cpp_name,
            enum_name=enum_decl.name,
            enum_values=enum_values,
        )

    def write(self, work_dir: str) -> None:
        """
        Write the hpp and cpp wrapper code to file.

        All of a class's template instantiations share a single
        `{class}.cppwg.hpp` / `.cpp` pair. The cpp holds one shared preamble
        followed by one registration block per instantiation.

        Parameters
        ----------
        work_dir : str
            The directory to write the files to
        """
        logger = logging.getLogger()

        # decls, cpp_names and py_names are parallel, one entry per instantiation,
        # and the loop below indexes all three by the same position. Validate they
        # are the same length up-front so a mismatch fails deterministically here
        # rather than as an IndexError (or a mislabelled wrapper) mid-loop.
        n_decls = len(self.class_info.decls)
        n_cpp = len(self.class_info.cpp_names)
        n_py = len(self.class_info.py_names)
        if not n_decls == n_cpp == n_py:
            message = (
                f"Class {self.class_info.name} has mismatched instantiation lists "
                f"({n_decls} decls, {n_cpp} cpp_names, {n_py} py_names); they must "
                "be kept in lockstep."
            )
            logger.error(message)
            raise AssertionError(message)

        register_blocks: list[str] = []
        register_py_names: list[str] = []
        class_typedefs: list[str] = []
        deduped_typedefs: list[str] = []
        seen_typedefs: set[str] = set()

        for idx, class_decl in enumerate(self.class_info.decls):
            class_py_name = self.class_info.py_names[idx]

            # The alias typedef (typedef <cpp> <py>;) for this instantiation, kept
            # for the preamble so every block can refer to it (and every other
            # instantiation) by its alias regardless of block order.
            alias_typedef = "typedef {cpp_name} {py_name};\n".format(
                cpp_name=self.class_info.cpp_names[idx],
                py_name=class_py_name,
            )

            # A struct wrapping a single nested enum is a legacy special case, e.g.:
            #   struct Foo { enum Value {A, B, C}; };
            # registered as a py::enum_. Any other struct is a normal class (its
            # members are public by default) and falls through to the class path
            # below; without this it would be silently dropped, leaving the module's
            # unconditional include/register call pointing at a missing file.
            if type_traits_classes.is_struct(class_decl):
                enums = class_decl.enumerations(allow_empty=True)
                if len(enums) == 1:
                    register_blocks.append(self.build_struct_enum_register(idx))
                    register_py_names.append(class_py_name)
                    class_typedefs.append(alias_typedef)
                    continue

            block, return_typedefs = self.build_class_register(idx)
            register_blocks.append(block)
            register_py_names.append(class_py_name)
            class_typedefs.append(alias_typedef)

            # Hoist trampoline return typedefs into the shared preamble,
            # deduplicated so a type shared by several instantiations (e.g.
            # ::std::string) is not redefined.
            for line in return_typedefs.splitlines(keepends=True):
                if line not in seen_typedefs:
                    seen_typedefs.add(line)
                    deduped_typedefs.append(line)

        # Nothing to register - write no files. The module writer still emits an
        # include and register_..._class call for this class, so warn loudly rather
        # than let it surface later as an opaque missing-header compile error.
        if not register_blocks:
            logger.warning(
                f"Class {self.class_info.name} produced no wrapper code; no file "
                "written. Its module include/register call will not resolve."
            )
            return

        # Assemble the preamble typedef blocks and the register section once; each
        # feeds both the type-caster scan and the emitted cpp, so join a single
        # time rather than repeating the work. register_section carries the exact
        # separator (a leading newline) that goes between the preamble and the
        # register blocks in the emitted file, so it is a single source of truth
        # for that boundary.
        class_typedefs_block = "".join(class_typedefs)
        return_typedefs_block = "".join(deduped_typedefs)
        register_section = "\n" + "\n".join(register_blocks)

        # Detect which type-caster headers this class needs by scanning the
        # generated registration text (the alias/trampoline typedefs and the
        # register blocks) for the configured caster types. Scanning the emitted
        # code means only types that actually survived into the wrapper count, so
        # exclusions are honoured automatically. scan_text is assembled from the
        # same pieces (and the same separator) as the emitted cpp below, so it is
        # exactly the tail of the wrapper text from the typedefs onward - the scan
        # never diverges from what is written. Must run before build_cpp_header,
        # which emits the includes via includes_block().
        scan_text = class_typedefs_block + return_typedefs_block + register_section
        self.typecaster_includes = self._detect_typecasters(scan_text)

        self.hpp_string = self.build_hpp(register_py_names)
        self.cpp_string = self.build_cpp_header(
            class_typedefs_block, return_typedefs_block
        )
        self.cpp_string += register_section
        self.write_files(work_dir, self.class_info.py_name_base())

    def _detect_typecasters(self, scan_text: str) -> list[str]:
        """
        Return the type-caster headers whose types appear in the wrapper code.

        Iterates the package's already-validated typecasters
        (`PackageInfo.parsed_typecasters`, reached via the info tree) and
        includes an entry's header if any of its type names occurs as a whole
        token in `scan_text` (the generated registration code). The result
        preserves config order and is de-duplicated, so a header is emitted once
        even if it matches several types or several instantiations.

        The entries are validated (and any malformed-entry warnings emitted) once
        on PackageInfo, not per class wrapper, so a bad entry does not warn once
        per class.

        Parameters
        ----------
        scan_text : str
            The generated registration text to search (typedefs + register
            blocks).

        Returns
        -------
        list[str]
            The caster header filenames to include, in config order.
        """
        entries = self.class_info.hierarchy_attribute("parsed_typecasters")
        if not entries:
            return []

        headers: list[str] = []
        for header, types in entries:
            if header in headers:
                continue
            if any(type_string_matches(scan_text, type_name) for type_name in types):
                headers.append(header)

        return headers

    def write_files(self, work_dir: str, file_stem: str) -> None:
        """
        Write the hpp and cpp wrapper code to file.

        Parameters
        ----------
            work_dir : str
                The directory to write the files to
            file_stem : str
                The wrapper file stem shared by all of the class's
                instantiations, e.g. Foo (for Foo.cppwg.hpp / Foo.cppwg.cpp).
        """
        hpp_filepath = os.path.join(work_dir, f"{file_stem}.{CPPWG_EXT}.hpp")
        cpp_filepath = os.path.join(work_dir, f"{file_stem}.{CPPWG_EXT}.cpp")

        write_file_if_changed(hpp_filepath, self.hpp_string, self.overwrite)
        write_file_if_changed(cpp_filepath, self.cpp_string, self.overwrite)
