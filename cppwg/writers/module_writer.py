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
        cpp_string = ""

        # Add the top prefix text
        prefix_text = self.module_info.hierarchy_attribute("prefix_text")
        if prefix_text:
            cpp_string += prefix_text + "\n"

        # Add top level includes
        cpp_string += "#include <pybind11/pybind11.h>\n"

        if self.module_info.package_info.common_include_file:
            cpp_string += f'#include "{CPPWG_HEADER_COLLECTION_FILENAME}"\n'
        else:
            # Include the headers that declare any exception classes so the
            # generated exception translator can reference them. When a common
            # include file is used these are already available via the header
            # collection.
            seen = set()
            for exception in self.module_info.package_info.exception_info:
                source_file = exception["source_file"]
                if source_file not in seen:
                    seen.add(source_file)
                    cpp_string += f'#include "{source_file}"\n'

        # Add outputs from running custom generator code
        if self.module_info.custom_generator_instance:
            cpp_string += (
                self.module_info.custom_generator_instance.get_module_pre_code()
            )

        # Add includes for class wrappers in the module
        for class_info in self.module_info.class_collection:
            # Skip excluded classes
            if class_info.excluded:
                continue

            for py_name in class_info.py_names:
                # Example: #include "Foo_2_2.cppwg.hpp"
                cpp_string += f'#include "{py_name}.{CPPWG_EXT}.hpp"\n'

        # Format module name as _packagename_modulename
        full_module_name = (
            f"_{self.module_info.package_info.name}_{self.module_info.name}"
        )

        # Create the pybind11 module
        cpp_string += "\nnamespace py = pybind11;\n"
        cpp_string += f"\nPYBIND11_MODULE({full_module_name}, m)\n"
        cpp_string += "{\n"

        # Import any modules that register externally-wrapped base classes, so
        # that those base types exist before this module's classes (which may
        # derive from them) are registered. See `imports` in the module config.
        if self.module_info.imports:
            for import_name in self.module_info.imports:
                cpp_string += f'    py::module_::import("{import_name}");\n'
            cpp_string += "\n"

        # Register a pybind11 exception translator for the configured exception
        # classes so that C++ exceptions surface as Python exceptions
        cpp_string += self.generate_exception_translator()

        # Add free functions
        for free_function_info in self.module_info.free_function_collection:
            function_writer = CppFreeFunctionWrapperWriter(
                free_function_info, self.wrapper_templates
            )
            cpp_string += function_writer.generate_wrapper()

        # Add classes
        for class_info in self.module_info.class_collection:
            # Skip excluded classes
            if class_info.excluded:
                continue

            for py_name in class_info.py_names:
                # Example: register_Foo_2_2_class(m);"
                cpp_string += f"    register_{py_name}_class(m);\n"

        # Add code from the module's custom generator
        if self.module_info.custom_generator_instance:
            cpp_string += self.module_info.custom_generator_instance.get_module_code()

        cpp_string += "}\n"  # End of the pybind11 module

        # Write to /path/to/wrapper_root/modulename/modulename.main.cpp
        module_dir = os.path.join(self.wrapper_root, self.module_info.name)
        if not os.path.isdir(module_dir):
            os.makedirs(module_dir)

        module_cpp_file = os.path.join(
            module_dir, f"{full_module_name}.main.{CPPWG_EXT}.cpp"
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
