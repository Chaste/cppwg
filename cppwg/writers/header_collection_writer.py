"""Writer for header collection hpp file."""

import os
from typing import TYPE_CHECKING

from cppwg.info.class_info import CppClassInfo
from cppwg.info.free_function_info import CppFreeFunctionInfo
from cppwg.info.package_info import PackageInfo
from cppwg.utils import utils
from cppwg.utils.utils import write_file_if_changed

if TYPE_CHECKING:
    from string import Template


class CppHeaderCollectionWriter:
    """
    Class to manage the generation of the header collection file.

    The header collection file includes all the headers to be parsed by CastXML.
    It also contains explicit template instantiations and their corresponding
    typedefs (e.g. typedef Foo<2,2> Foo_2_2) for all classes that are to be
    automatically wrapped.

    Attributes
    ----------
        package_info : PackageInfo
            The package information
        wrapper_templates : dict[str, Template]
            Templates with placeholders for generating wrapper code
        wrapper_root : str
            The output directory for the generated wrapper code
        hpp_collection_file : str
            The path to save the header collection file to
        overwrite : bool
            Force rewrite of the header collection file, even if unchanged
        hpp_collection : str
            The output string that gets written to the header collection file
        class_dict : dict[str, CppClassInfo]
            A dictionary of all class info objects
        free_func_dict : dict[str, CppFreeFunctionInfo]
            A dictionary of all free function info objects
    """

    def __init__(
        self,
        package_info: PackageInfo,
        wrapper_templates: dict[str, "Template"],
        wrapper_root: str,
        hpp_collection_file: str,
        overwrite: bool = False,
    ):
        self.package_info: PackageInfo = package_info
        self.wrapper_templates: dict[str, "Template"] = wrapper_templates
        self.wrapper_root: str = wrapper_root
        self.hpp_collection_file: str = hpp_collection_file
        self.overwrite: bool = overwrite
        self.hpp_collection: str = ""

        # For convenience, collect all class and free function info into dicts keyed by name
        self.class_dict: dict[str, CppClassInfo] = {}
        self.free_func_dict: dict[str, CppFreeFunctionInfo] = {}

        for module_info in self.package_info.module_collection:
            for class_info in module_info.class_collection:
                self.class_dict[class_info.name] = class_info

            for free_function_info in module_info.free_function_collection:
                self.free_func_dict[free_function_info.name] = free_function_info

    def should_include_all(self) -> bool:
        """
        Return whether all source files in the module source locations should be included.

        Returns
        -------
        bool
        """
        # True if any module uses all classes or all free functions
        for module_info in self.package_info.module_collection:
            if module_info.use_all_classes or module_info.use_all_free_functions:
                return True
        return False

    def includes_block(self) -> str:
        """
        Build the `#include` block for the header collection file.

        Returns
        -------
        str
            The include directives, one per line.
        """
        includes = ""
        seen_files = set()  # Keep track of included files to avoid duplicates

        if self.should_include_all():
            # Include all the headers
            for filepath in self.package_info.source_hpp_files:
                filename = os.path.basename(filepath)
                if filename not in seen_files:
                    includes += f'#include "{filename}"\n'
                    seen_files.add(filename)

        else:
            # Include specific headers needed by classes
            for module_info in self.package_info.module_collection:
                for class_info in module_info.class_collection:
                    # Skip excluded classes
                    if class_info.excluded:
                        continue

                    filename = class_info.source_file
                    if filename and filename not in seen_files:
                        includes += f'#include "{filename}"\n'
                        seen_files.add(filename)

                # Include specific headers needed by free functions
                for free_function_info in module_info.free_function_collection:
                    if free_function_info.source_file_path:
                        filename = os.path.basename(free_function_info.source_file_path)
                        if filename not in seen_files:
                            includes += f'#include "{filename}"\n'
                            seen_files.add(filename)

            # Include headers that declare the configured exception classes so
            # they are parsed and can be introspected for the translator. Read
            # each header at most once - mapping each exception to the first
            # header that declares it - rather than re-reading every header for
            # each exception name.
            exception_names = self.package_info.exception_names
            if exception_names:
                exception_files: dict[str, str] = {}
                remaining = set(exception_names)
                for filepath in self.package_info.source_hpp_files:
                    if not remaining:
                        break
                    class_names = {
                        name
                        for _, name, _ in utils.find_classes_in_source_file(filepath)
                    }
                    for name in remaining & class_names:
                        exception_files[name] = filepath
                    remaining -= class_names

                # Emit includes in exception-name order, as before.
                for exception_name in exception_names:
                    filepath = exception_files.get(exception_name)
                    if filepath is None:
                        continue
                    filename = os.path.basename(filepath)
                    if filename not in seen_files:
                        includes += f'#include "{filename}"\n'
                        seen_files.add(filename)

        return includes

    def template_blocks(self) -> tuple[str, str]:
        """
        Build the template instantiation and typedef blocks.

        Returns
        -------
        tuple[str, str]
            The instantiations e.g. `template class Foo<2,2>;` and the typedefs
            e.g. `    typedef Foo<2,2> Foo_2_2;`, one item per line.
        """
        template_instantiations = ""
        template_typedefs = ""

        for module_info in self.package_info.module_collection:
            for class_info in module_info.class_collection:
                # Skip excluded classes
                if class_info.excluded:
                    continue

                # Skip untemplated classes
                if not class_info.template_arg_lists:
                    continue

                # C++ class names eg. ["Foo<2,2>", "Foo<3,3>"]
                cpp_names = [name.strip() for name in class_info.cpp_names]

                # Python class names eg. ["Foo_2_2", "Foo_3_3"]
                py_names = [name.strip() for name in class_info.py_names]

                for cpp_name, py_name in zip(cpp_names, py_names):
                    template_instantiations += f"template class {cpp_name};\n"
                    template_typedefs += f"    typedef {cpp_name} {py_name};\n"

        return template_instantiations, template_typedefs

    def write(self) -> None:
        """Generate the header file output string and write it to file."""
        prefix_text = self.package_info.hierarchy_attribute("prefix_text")
        template_instantiations, template_typedefs = self.template_blocks()

        self.hpp_collection = self.wrapper_templates["header_collection_hpp"].substitute(
            prefix_text=f"{prefix_text}\n" if prefix_text else "",
            guard=f"{self.package_info.name}_HEADERS_HPP_",
            includes=self.includes_block(),
            template_instantiations=template_instantiations,
            template_typedefs=template_typedefs,
        )

        # Write the header collection string to file
        write_file_if_changed(
            self.hpp_collection_file, self.hpp_collection, self.overwrite
        )
