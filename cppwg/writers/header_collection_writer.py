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
        # True if any module uses all classes, free functions or enums
        for module_info in self.package_info.module_collection:
            if (
                module_info.use_all_classes
                or module_info.use_all_free_functions
                or module_info.use_all_enums
            ):
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
        # Collect the header filenames, then emit them sorted, so the output is
        # deterministic (independent of class order or when each class's source
        # file was resolved) and the collection can be safely re-written after
        # pruning without spuriously reordering.
        include_files: set[str] = set()

        if self.should_include_all():
            # Include all the headers
            for filepath in self.package_info.source_hpp_files:
                include_files.add(os.path.basename(filepath))

        else:
            # Include specific headers needed by classes
            for module_info in self.package_info.module_collection:
                for class_info in module_info.class_collection:
                    # Skip excluded classes
                    if class_info.excluded:
                        continue

                    if class_info.source_file:
                        include_files.add(class_info.source_file)

                # Include specific headers needed by free functions
                for free_function_info in module_info.free_function_collection:
                    if free_function_info.source_file_path:
                        include_files.add(
                            os.path.basename(free_function_info.source_file_path)
                        )

                # Include specific headers needed by enums
                for enum_info in module_info.enum_collection:
                    if enum_info.source_file_path:
                        include_files.add(
                            os.path.basename(enum_info.source_file_path)
                        )

            # Include headers that declare the configured exception classes so
            # they are parsed and can be introspected for the translator. Read
            # each header at most once - mapping each exception to the first
            # header that declares it - rather than re-reading every header for
            # each exception name.
            exception_names = self.package_info.exception_names
            if exception_names:
                remaining = set(exception_names)
                for filepath in self.package_info.source_hpp_files:
                    if not remaining:
                        break
                    class_names = {
                        name
                        for _, name, _ in utils.find_classes_in_source_file(filepath)
                    }
                    for _ in remaining & class_names:
                        include_files.add(os.path.basename(filepath))
                    remaining -= class_names

        return "".join(f'#include "{filename}"\n' for filename in sorted(include_files))

    def template_blocks(self) -> tuple[str, str]:
        """
        Build the template instantiation and typedef blocks.

        Returns
        -------
        tuple[str, str]
            The instantiations e.g. `template class Foo<2,2>;` and the typedefs
            e.g. `    typedef Foo<2,2> Foo_2_2;`, one item per line.
        """
        # Collect (C++ name, Python name) pairs then emit them sorted, so the
        # output is deterministic and the collection can be safely re-written
        # after pruning without spuriously reordering.
        pairs: list[tuple[str, str]] = []

        for module_info in self.package_info.module_collection:
            for class_info in module_info.class_collection:
                # Skip excluded classes
                if class_info.excluded:
                    continue

                # Skip untemplated classes
                if not class_info.template_arg_lists:
                    continue

                # C++ names eg. ["Foo<2,2>"], Python names eg. ["Foo_2_2"]
                cpp_names = [name.strip() for name in class_info.cpp_names]
                py_names = [name.strip() for name in class_info.py_names]
                pairs.extend(zip(cpp_names, py_names))

        pairs.sort()

        template_instantiations = "".join(
            f"template class {cpp_name};\n" for cpp_name, _ in pairs
        )
        template_typedefs = "".join(
            f"    typedef {cpp_name} {py_name};\n" for cpp_name, py_name in pairs
        )

        return template_instantiations, template_typedefs

    def write(self) -> None:
        """Generate the header file output string and write it to file."""
        prefix_text = self.package_info.hierarchy_attribute("prefix_text")
        template_instantiations, template_typedefs = self.template_blocks()

        self.hpp_collection = self.wrapper_templates[
            "header_collection_hpp"
        ].substitute(
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
