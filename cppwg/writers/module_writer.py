import os
import logging

from typing import Dict

from pygccxml.declarations.class_declaration import class_t
from pygccxml.declarations.namespace import namespace_t

from cppwg.input.module_info import ModuleInfo

from cppwg.writers.free_function_writer import CppFreeFunctionWrapperWriter
from cppwg.writers.class_writer import CppClassWrapperWriter

from cppwg.utils.constants import CPPWG_EXT
from cppwg.utils.constants import CPPWG_HEADER_COLLECTION_FILENAME


class CppModuleWrapperWriter:
    """
    This class automatically generates Python bindings using a rule based approach

    Attributes
    ----------
    source_ns : namespace_t
        The pygccxml namespace containing declarations from the source code
    module_info : ModuleInfo
        The module information to generate Python bindings for
    wrapper_templates : Dict[str, str]
        String templates with placeholders for generating wrapper code
    wrapper_root : str
        The output directory for the generated wrapper code
    package_license : str
        The license to include in the generated wrapper code
    exposed_class_full_names : List[str]
        A list of full names of all classes to be wrapped in the module
    """

    def __init__(
        self,
        source_ns: namespace_t,
        module_info: ModuleInfo,
        wrapper_templates: Dict[str, str],
        wrapper_root: str,
        package_license: str = "",
    ):
        self.source_ns: namespace_t = source_ns
        self.module_info: ModuleInfo = module_info
        self.wrapper_templates: Dict[str, str] = wrapper_templates
        self.wrapper_root: str = wrapper_root
        self.package_license: str = (
            package_license  # TODO: use this in the generated wrappers
        )

        # For convenience, create a list of all classes to be wrapped in the module
        # e.g. ['Foo', 'Bar<2>', 'Bar<3>']
        self.exposed_class_full_names: List[str] = []

        for class_info in self.module_info.class_info_collection:
            for full_name in class_info.get_full_names():
                self.exposed_class_full_names.append(full_name.replace(" ", ""))

    def write_module_wrapper(self) -> None:
        """
        Generate the contents of the main cpp file for the module and write it
        to modulename.main.cpp. This file contains the pybind11 module
        definition. Within the module definition, the module's free functions
        and classes are registered.

        For example, the generated file might look like this:

        ```
        #include <pybind11/pybind11.h>
        #include "Foo.cppwg.hpp"

        PYBIND11_MODULE(_packagename_modulename, m)
        {
            register_Foo_class(m);
        }
        ```
        """

        # Add top level includes
        cpp_string = "#include <pybind11/pybind11.h>\n"

        if self.module_info.package_info.common_include_file:
            cpp_string += f'#include "{CPPWG_HEADER_COLLECTION_FILENAME}"\n'

        # Add outputs from running custom generator code
        if self.module_info.custom_generator:
            cpp_string += self.module_info.custom_generator.get_module_pre_code()

        # Add includes for class wrappers in the module
        for class_info in self.module_info.class_info_collection:
            for short_name in class_info.get_short_names():
                # Example: #include "Foo2_2.cppwg.hpp"
                cpp_string += f'#include "{short_name}.{CPPWG_EXT}.hpp"\n'

        # Format module name as _packagename_modulename
        full_module_name = (
            "_" + self.module_info.package_info.name + "_" + self.module_info.name
        )

        # Create the pybind11 module
        cpp_string += "\nnamespace py = pybind11;\n"
        cpp_string += f"\nPYBIND11_MODULE({full_module_name}, m)\n"
        cpp_string += "{\n"

        # Add free functions
        for free_function_info in self.module_info.free_function_info_collection:
            function_writer = CppFreeFunctionWrapperWriter(
                free_function_info, self.wrapper_templates
            )
            # TODO: Consider returning the function string instead
            cpp_string = function_writer.add_self(cpp_string)

        # Add classes
        for class_info in self.module_info.class_info_collection:
            for short_name in class_info.get_short_names():
                # Example: register_Foo2_2_class(m);"
                cpp_string += f"    register_{short_name}_class(m);\n"

        # Add code from the module's custom generator
        if self.module_info.custom_generator:
            cpp_string += self.module_info.custom_generator.get_module_code()

        cpp_string += "}\n"  # End of the pybind11 module

        # Write to /path/to/wrapper_root/modulename/modulename.main.cpp
        module_dir = os.path.join(self.wrapper_root, self.module_info.name)
        if not os.path.isdir(module_dir):
            os.makedirs(module_dir)

        module_cpp_file = os.path.join(module_dir, self.module_info.name + ".main.cpp")

        with open(module_cpp_file, "w") as out_file:
            out_file.write(cpp_string)

    def write_class_wrappers(self) -> None:
        """
        Write wrappers for classes in the module
        """
        logger = logging.getLogger()

        for class_info in self.module_info.class_info_collection:
            logger.info(f"Generating wrapper for class {class_info.name}")

            class_writer = CppClassWrapperWriter(
                class_info, self.wrapper_templates, self.exposed_class_full_names
            )

            # Get the declaration for each class and add it to the class writer
            # TODO: Consider using class_info.decl instead
            for full_name in class_info.get_full_names():
                name = full_name.replace(" ", "")  # e.g. Foo<2,2>

                class_decl: class_t = self.source_ns.class_(name)
                class_writer.class_decls.append(class_decl)

            # Write the class wrappers into /path/to/wrapper_root/modulename/
            module_dir = os.path.join(self.wrapper_root, self.module_info.name)
            class_writer.write(module_dir)

    def write(self) -> None:
        """
        Main method for writing the module
        """
        logger = logging.getLogger()

        logger.info(f"Generating wrappers for module {self.module_info.name}")

        self.write_module_wrapper()
        self.write_class_wrappers()
