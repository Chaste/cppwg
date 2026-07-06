"""Wrapper code writer for modules."""

import logging
import os
from typing import Dict, Set

from cppwg.utils.constants import CPPWG_EXT, CPPWG_HEADER_COLLECTION_FILENAME
from cppwg.utils.utils import write_file_if_changed
from cppwg.writers.class_writer import CppClassWrapperWriter
from cppwg.writers.free_function_writer import CppFreeFunctionWrapperWriter


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
    wrapper_templates : Dict[str, str]
        String templates with placeholders for generating wrapper code
    wrapper_root : str
        The output directory for the generated wrapper code
    overwrite : bool
        Force rewrite of all wrapper files, even if unchanged

    classes : Dict[pygccxml.declarations.class_t, str]
        A dictionary of decls and names for all classes to be wrapped in the module
    """

    def __init__(
        self,
        module_info: "ModuleInfo",  # noqa: F821
        wrapper_templates: Dict[str, str],
        wrapper_root: str,
        overwrite: bool = False,
    ):
        self.module_info: "ModuleInfo" = module_info  # noqa: F821
        self.wrapper_templates: Dict[str, str] = wrapper_templates
        self.wrapper_root: str = wrapper_root
        self.overwrite: bool = overwrite

        # For convenience, store a dictionary of decl->name pairs for all
        # classes to be wrapped in the module
        self.classes: Dict["class_t", str] = {}  # noqa: F821

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
        self.package_classes: Set["class_t"] = set()  # noqa: F821
        for module_info in self.module_info.package_info.module_collection:
            for class_info in module_info.class_collection:
                if class_info.excluded:
                    continue
                self.package_classes.update(class_info.decls)

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

        code = "    py::register_exception_translator([](std::exception_ptr p) {\n"
        code += "        try {\n"
        code += "            if (p) std::rethrow_exception(p);\n"
        for exception in exception_info:
            code += f"        }} catch (const {exception['cpp_type']}& e) {{\n"
            code += (
                "            PyErr_SetString(PyExc_RuntimeError, "
                f"{exception['message_expr']});\n"
            )
        code += "        }\n"
        code += "    });\n\n"
        return code

    @property
    def full_module_name(self) -> str:
        """Return the pybind11 module name, e.g. `_packagename_modulename`."""
        return f"_{self.module_info.package_info.name}_{self.module_info.name}"

    def build_module_context(self) -> Dict[str, str]:
        """
        Build the substitution blocks for the module's main cpp template.

        Each value is a fully-formed string block (including its own trailing
        newlines, or empty) that is dropped into the `module_main_cpp` template.
        All the iteration and conditional logic lives here; the template only
        places the resulting blocks.

        Returns
        -------
        Dict[str, str]
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

        # Top level includes
        if package_info.common_include_file:
            includes = f'#include "{CPPWG_HEADER_COLLECTION_FILENAME}"\n'
        else:
            # Include the headers that declare any exception classes so the
            # generated exception translator can reference them. When a common
            # include file is used these are already available via the header
            # collection.
            seen = set()
            include_lines = []
            for exception in package_info.exception_info:
                source_file = exception["source_file"]
                if source_file not in seen:
                    seen.add(source_file)
                    include_lines.append(f'#include "{source_file}"\n')
            includes = "".join(include_lines)

        # Includes for class wrappers in the module
        # Example: #include "Foo_2_2.cppwg.hpp"
        class_includes = "".join(
            f'#include "{py_name}.{CPPWG_EXT}.hpp"\n'
            for class_info in non_excluded_classes
            for py_name in class_info.py_names
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

        # Free functions
        free_functions = "".join(
            CppFreeFunctionWrapperWriter(
                free_function_info, self.wrapper_templates
            ).generate_wrapper()
            for free_function_info in module_info.free_function_collection
        )

        # Class registration calls, e.g. register_Foo_2_2_class(m);
        register_calls = "".join(
            f"    register_{py_name}_class(m);\n"
            for class_info in non_excluded_classes
            for py_name in class_info.py_names
        )

        return {
            "prefix_text": prefix_block,
            "includes": includes,
            "module_pre_code": (
                generator.get_module_pre_code() if generator else ""
            ),
            "class_includes": class_includes,
            "full_module_name": self.full_module_name,
            "imports": imports,
            # Register a pybind11 exception translator for the configured
            # exception classes so C++ exceptions surface as Python exceptions.
            "exception_translator": self.generate_exception_translator(),
            "free_functions": free_functions,
            "register_calls": register_calls,
            "module_code": generator.get_module_code() if generator else "",
        }

    def write_module_wrapper(self) -> None:
        """
        Generate the contents of the main cpp file for the module.

        The main cpp file is named `modulename.main.cpp`. This file contains the
        pybind11 module definition, within which the module's classes and free
        functions are registered.

        Example output:

        ```
        #include <pybind11/pybind11.h>
        #include "Foo.cppwg.hpp"
        #include "Bar.cppwg.hpp"

        PYBIND11_MODULE(_packagename_modulename, m)
        {
            register_Foo_class(m);
            register_Bar_class(m);
        }
        ```
        """
        cpp_string = self.wrapper_templates["module_main_cpp"].substitute(
            self.build_module_context()
        )

        # Write to /path/to/wrapper_root/modulename/modulename.main.cpp
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

        for class_info in self.module_info.class_collection:
            # Skip excluded classes
            if class_info.excluded:
                logger.info(f"Skipping class {class_info.name}")
                continue

            logger.info(f"Generating wrappers for class {class_info.name}")

            class_writer = CppClassWrapperWriter(
                class_info,
                self.wrapper_templates,
                self.classes,
                self.package_classes,
                self.overwrite,
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
