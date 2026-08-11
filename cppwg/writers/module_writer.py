"""Wrapper code writer for modules."""

import logging
import os
from typing import TYPE_CHECKING

from cppwg.utils.constants import CPPWG_EXT, CPPWG_HEADER_COLLECTION_FILENAME
from cppwg.utils.utils import (
    call_generator_hook,
    ensure_trailing_newline,
    registration_function_name,
    write_file_if_changed,
)
from cppwg.writers.class_writer import CppClassWrapperWriter
from cppwg.writers.enum_writer import CppEnumWrapperWriter
from cppwg.writers.free_function_writer import CppFreeFunctionWrapperWriter

if TYPE_CHECKING:
    from string import Template

    from pygccxml.declarations.class_declaration import class_t

    from cppwg.info.class_info import CppClassInfo
    from cppwg.info.module_info import ModuleInfo


class CppModuleWrapperWriter:
    """
    Class to automatically generates Python bindings for modules.

    A module is a collection of classes and free functions that are to be
    wrapped in Python. The module writer generates the main cpp file for the
    module, which contains the pybind11 module definition. Within the module
    definition, the module's free functions and classes are registered.

    Attributes
    ----------
    module_info : ModuleInfo
        The module information to generate Python bindings for
    wrapper_templates : dict[str, Template]
        Templates with placeholders for generating wrapper code
    wrapper_root : str
        The output directory for the generated wrapper code
    overwrite : bool
        Force rewrite of all wrapper files, even if unchanged

    classes : dict[pygccxml.declarations.class_t, str]
        A dictionary of decls and names for all classes to be wrapped in the module
    """

    def __init__(
        self,
        module_info: "ModuleInfo",
        wrapper_templates: dict[str, "Template"],
        wrapper_root: str,
        overwrite: bool = False,
    ):
        self.module_info: "ModuleInfo" = module_info
        self.wrapper_templates: dict[str, "Template"] = wrapper_templates
        self.wrapper_root: str = wrapper_root
        self.overwrite: bool = overwrite

        # For convenience, store a dictionary of decl->name pairs for all
        # classes to be wrapped in the module
        self.classes: dict["class_t", str] = {}

        for class_info in self.module_info.class_collection:
            # Skip excluded classes
            if class_info.excluded:
                continue

            for decl, cpp_name in zip(class_info.decls, class_info.cpp_names):
                self.classes[decl] = cpp_name

        # Declarations for every class wrapped anywhere in this package (across
        # all of its modules). Used to detect base classes that are wrapped in a
        # different module of the same package, which are therefore known to be
        # registered and safe to reference as external bases.
        #
        # package_class_infos maps each such decl back to its class_info, so the
        # inherited-override skip can consult a base class's excluded_methods (a
        # base method excluded there is not wrapped, so its override must be kept).
        self.package_classes: set["class_t"] = set()
        self.package_class_infos: dict["class_t", "CppClassInfo"] = {}
        for module_info in self.module_info.package_info.module_collection:
            for class_info in module_info.class_collection:
                if class_info.excluded:
                    continue
                self.package_classes.update(class_info.decls)
                for decl in class_info.decls:
                    self.package_class_infos[decl] = class_info

    def generate_exception_translator(self) -> str:
        """
        Generate a pybind11 exception translator for the package's exceptions.

        Produces a `py::register_exception_translator` call with a catch clause
        for each configured exception class, mapping it to a Python
        RuntimeError. Returns an empty string if no exceptions are configured.

        Returns
        -------
        str
            The exception translator code, indented for the module body.
        """
        exception_info = self.module_info.package_info.exception_info
        if not exception_info:
            return ""

        catch_template = self.wrapper_templates["module_exception_catch"]
        catch_clauses = "".join(
            catch_template.substitute(
                cpp_type=exception["cpp_type"],
                message_expr=exception["message_expr"],
            )
            for exception in exception_info
        )

        return self.wrapper_templates["module_exception_translator"].substitute(
            catch_clauses=catch_clauses
        )

    @property
    def full_module_name(self) -> str:
        """Return the pybind11 module name, e.g. `_packagename_modulename`."""
        return f"_{self.module_info.package_info.name}_{self.module_info.name}"

    def build_module_context(self) -> dict[str, str]:
        """
        Build the substitution blocks for the module's main cpp template.

        Each value is a fully-formed string block (including its own trailing
        newlines, or empty) that is dropped into the `module_main_cpp` template.
        All the iteration and conditional logic lives here; the template only
        places the resulting blocks.

        Returns
        -------
        dict[str, str]
            A mapping of template placeholder names to code blocks.
        """
        module_info = self.module_info
        package_info = module_info.package_info
        generator = module_info.custom_generator_instance

        non_excluded_classes = [
            class_info
            for class_info in module_info.class_collection
            if not class_info.excluded
        ]

        # Top prefix text
        prefix_text = module_info.hierarchy_attribute("prefix_text")
        prefix_block = f"{prefix_text}\n" if prefix_text else ""

        # Headers that declare the configured exception classes, so the generated
        # translator can catch them. They are wrapped in a default-visibility
        # pragma: the module is built with -fvisibility=hidden (pybind11's
        # default), under which a header-only exception type's type_info is unique
        # to each shared object, so the translator (in the module) would fail to
        # match an exception thrown in another library and fall back to what().
        # Exporting the type coalesces its type_info across that boundary. These
        # are emitted first so the (include-guarded) header is first seen with
        # this visibility even when it is also pulled in via the header collection.
        seen = set()
        exception_includes = []
        for exception in package_info.exception_info:
            source_file = exception["source_file"]
            if source_file and source_file not in seen:
                seen.add(source_file)
                exception_includes.append(f'#include "{source_file}"\n')
        exception_block = ""
        if exception_includes:
            exception_block = (
                "#ifdef __GNUC__\n"
                "#pragma GCC visibility push(default)\n"
                "#endif\n" + "".join(exception_includes) + "#ifdef __GNUC__\n"
                "#pragma GCC visibility pop\n"
                "#endif\n"
            )

        # Top level includes
        if package_info.common_include_file:
            includes = (
                exception_block + f'#include "{CPPWG_HEADER_COLLECTION_FILENAME}"\n'
            )
        else:
            includes = exception_block

        # Includes for class wrappers in the module. All of a class's template
        # instantiations share one wrapper hpp (named after the class), so this
        # is one include per class, e.g. #include "Foo.cppwg.hpp".
        class_includes = "".join(
            f'#include "{class_info.py_name_base()}.{CPPWG_EXT}.hpp"\n'
            for class_info in non_excluded_classes
        )

        # Import any modules that register externally-wrapped base classes, so
        # that those base types exist before this module's classes (which may
        # derive from them) are registered. See `imports` in the module config.
        imports = ""
        if module_info.imports:
            imports = (
                "".join(
                    f'    py::module_::import("{import_name}");\n'
                    for import_name in module_info.imports
                )
                + "\n"
            )

        # Enums. Registered before free functions and class register calls so an
        # enum used as a defaulted argument of a wrapped signature is already
        # registered when pybind11 materialises that default at import time.
        enums = "".join(
            CppEnumWrapperWriter(enum_info, self.wrapper_templates).generate_wrapper()
            for enum_info in module_info.enum_collection
        )

        # Free functions
        free_functions = "".join(
            CppFreeFunctionWrapperWriter(
                free_function_info, self.wrapper_templates
            ).generate_wrapper()
            for free_function_info in module_info.free_function_collection
        )

        # Class registration calls, e.g. register_Foo_2_2_class(m);
        register_calls = "".join(
            f"    {registration_function_name(py_name)}(m);\n"
            for class_info in non_excluded_classes
            for py_name in class_info.py_names
        )

        return {
            "prefix_text": prefix_block,
            "includes": includes,
            # Generator snippets carry no trailing-newline guarantee. module_pre_code
            # is followed by the class #include lines and module_code by the module's
            # closing brace, so normalise both to end with a newline (see
            # ensure_trailing_newline) to avoid producing invalid C++.
            "module_pre_code": ensure_trailing_newline(
                call_generator_hook(generator, "get_module_pre_code", "")
            ),
            "class_includes": class_includes,
            "full_module_name": self.full_module_name,
            "imports": imports,
            # Register a pybind11 exception translator for the configured
            # exception classes so C++ exceptions surface as Python exceptions.
            "exception_translator": self.generate_exception_translator(),
            "enums": enums,
            "free_functions": free_functions,
            "register_calls": register_calls,
            "module_code": ensure_trailing_newline(
                call_generator_hook(generator, "get_module_code", "")
            ),
        }

    def write_module_wrapper(self) -> None:
        """
        Generate the contents of the main cpp file for the module.

        The main cpp file is named ``_packagename_modulename.main.cppwg.cpp``.
        This file contains the pybind11 module definition, within which the
        module's classes and free functions are registered.

        Example output::

            #include <pybind11/pybind11.h>
            #include "Foo.cppwg.hpp"
            #include "Bar.cppwg.hpp"

            PYBIND11_MODULE(_packagename_modulename, m)
            {
                register_Foo_class(m);
                register_Bar_class(m);
            }
        """
        cpp_string = self.wrapper_templates["module_main_cpp"].substitute(
            self.build_module_context()
        )

        # Write to /path/to/wrapper_root/modulename/_packagename_modulename.main.cppwg.cpp
        module_dir = os.path.join(self.wrapper_root, self.module_info.name)
        if not os.path.isdir(module_dir):
            os.makedirs(module_dir)

        module_cpp_file = os.path.join(
            module_dir, f"{self.full_module_name}.main.{CPPWG_EXT}.cpp"
        )

        write_file_if_changed(module_cpp_file, cpp_string, self.overwrite)

    def write_class_wrappers(self) -> None:
        """Write wrappers for classes in the module."""
        logger = logging.getLogger()

        seen_file_stems: dict[str, str] = {}
        for class_info in self.module_info.class_collection:
            # Skip excluded classes
            if class_info.excluded:
                logger.info(f"Skipping class {class_info.name}")
                continue

            # Each class writes one wrapper file pair named after the class. Two
            # classes sharing that name would overwrite each other's files (and
            # collide on the register_..._class symbols), producing a broken
            # output set that only fails later at compile/link. Fail fast instead.
            file_stem = class_info.py_name_base()
            if file_stem in seen_file_stems:
                message = (
                    f"Wrapper file name '{file_stem}.{CPPWG_EXT}.*' is used by both "
                    f"class {seen_file_stems[file_stem]} and class "
                    f"{class_info.name}. Give one of them a distinct name_override."
                )
                logger.error(message)
                raise ValueError(message)
            seen_file_stems[file_stem] = class_info.name

            logger.info(f"Generating wrappers for class {class_info.name}")

            class_writer = CppClassWrapperWriter(
                class_info,
                self.wrapper_templates,
                self.classes,
                self.package_classes,
                self.overwrite,
                self.package_class_infos,
            )

            # Write the class wrappers into /path/to/wrapper_root/modulename/
            module_dir = os.path.join(self.wrapper_root, self.module_info.name)
            class_writer.write(module_dir)

    def write(self) -> None:
        """Generate the module and class wrappers."""
        logger = logging.getLogger()

        logger.info(f"Generating wrappers for module {self.module_info.name}")

        self.write_module_wrapper()
        self.write_class_wrappers()
