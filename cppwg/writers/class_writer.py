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
from cppwg.utils.utils import write_file_if_changed
from cppwg.writers.base_writer import CppBaseWrapperWriter
from cppwg.writers.constructor_writer import CppConstructorWrapperWriter
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
    overwrite : bool
        Force rewrite of the class wrapper files, even if unchanged
    has_shared_ptr : bool
        Whether the class uses shared pointers
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
    ) -> None:
        logger = logging.getLogger()

        super().__init__(wrapper_templates)

        self.class_info = class_info

        if len(self.class_info.cpp_names) != len(self.class_info.py_names):
            logger.error("C++ and Python class name lists should be the same length")
            raise AssertionError()

        self.module_classes = module_classes
        self.package_classes = package_classes if package_classes is not None else set()

        self.overwrite = overwrite

        self.has_shared_ptr: bool = True

        self.hpp_string: str = ""
        self.cpp_string: str = ""

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

    def includes_block(self) -> str:
        """
        Return the `#include` block for a class wrapper cpp file.

        Returns
        -------
        str
            The include directives, one per line.
        """
        if self.class_info.hierarchy_attribute("common_include_file"):
            return f'#include "{CPPWG_HEADER_COLLECTION_FILENAME}"\n'

        includes = ""

        source_includes = self.class_info.hierarchy_attribute_gather_flat(
            "source_includes"
        )

        for source_include in source_includes:
            # Skip a mis-typed non-string (or empty) entry, e.g. a yaml scalar.
            if not isinstance(source_include, str) or not source_include:
                continue
            if source_include.startswith("<"):
                # e.g. #include <string>
                includes += f"#include {source_include}\n"
            else:
                # e.g. #include "Foo.hpp"
                includes += f'#include "{source_include}"\n'

        source_file = self.class_info.source_file
        if not source_file:
            source_file = os.path.basename(self.class_info.decls[0].location.file_name)
        includes += f'#include "{source_file}"\n'

        return includes

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
        Return the base-class list appended to the py::class_ declaration.

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

    def build_cpp_header(self, return_typedefs: str) -> str:
        """
        Build the shared preamble of the class wrapper cpp file.

        Emitted once per class (not per instantiation): the includes, the smart
        pointer holder declaration, class-level prefix code, and the
        deduplicated trampoline return typedefs.

        Parameters
        ----------
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
            return_typedefs=return_typedefs,
        )

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
        return_typedefs, override_class, methods_needing_override = (
            self.virtual_overrides(template_idx)
        )

        # Add the trampoline override class to the class definition if needed
        # e.g. py::class_<Foo, Foo_Overrides>(m, "Foo")
        overrides_string = ""
        if methods_needing_override:
            overrides_string = f", {class_py_name}{CPPWG_CLASS_OVERRIDE_SUFFIX}"

        # Add smart pointer support to the wrapper class definition if needed
        # e.g. py::class_<Foo, boost::shared_ptr<Foo>>(m, "Foo")
        ptr_support = ""
        smart_ptr_type = self.class_info.hierarchy_attribute("smart_ptr_type")
        if self.has_shared_ptr and smart_ptr_type:
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

        # Add public member functions
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
        )

        block = self.wrapper_templates["class_cpp_register"].substitute(
            generator_pre_code=(
                generator.get_class_cpp_pre_code(class_py_name) if generator else ""
            ),
            class_py_name=class_py_name,
            class_cpp_name=class_cpp_name,
            override_class=override_class,
            overrides_string=overrides_string,
            ptr_support=ptr_support,
            bases=self.bases_block(class_decl),
            constructors=constructors,
            methods=methods,
            generator_def_code=(
                generator.get_class_cpp_def_code(class_py_name) if generator else ""
            ),
            suffix_code=self.suffix_code(),
        )
        return block, return_typedefs

    def build_struct_enum_register(self, template_idx: int) -> str:
        """
        Build the registration block for a struct-enum instantiation.

        Handles a struct that wraps a single nested enum, for example:

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
            generator_pre_code=(
                generator.get_class_cpp_pre_code(class_py_name) if generator else ""
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
        deduped_typedefs: list[str] = []
        seen_typedefs: set[str] = set()

        for idx, class_decl in enumerate(self.class_info.decls):
            class_py_name = self.class_info.py_names[idx]

            # Check for the struct-enum pattern, e.g.:
            #   struct Foo { enum Value {A, B, C}; };
            if type_traits_classes.is_struct(class_decl):
                enums = class_decl.enumerations(allow_empty=True)
                if len(enums) == 1:
                    register_blocks.append(self.build_struct_enum_register(idx))
                    register_py_names.append(class_py_name)
                continue

            block, return_typedefs = self.build_class_register(idx)
            register_blocks.append(block)
            register_py_names.append(class_py_name)

            # Hoist trampoline return typedefs into the shared preamble,
            # deduplicated so a type shared by several instantiations (e.g.
            # ::std::string) is not redefined.
            for line in return_typedefs.splitlines(keepends=True):
                if line not in seen_typedefs:
                    seen_typedefs.add(line)
                    deduped_typedefs.append(line)

        # Nothing to register (e.g. only structs that are not the single-enum
        # pattern) - write no files, matching the previous behaviour.
        if not register_blocks:
            return

        self.hpp_string = self.build_hpp(register_py_names)
        self.cpp_string = self.build_cpp_header("".join(deduped_typedefs))
        self.cpp_string += "\n" + "\n".join(register_blocks)
        self.write_files(work_dir, self.class_info.py_name_base())

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
