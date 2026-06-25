"""Writer for header collection hpp file."""

import os
from typing import Dict

from cppwg.info.class_info import CppClassInfo
from cppwg.info.free_function_info import CppFreeFunctionInfo
from cppwg.info.package_info import PackageInfo
from cppwg.utils.utils import write_file_if_changed


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
        wrapper_root : str
            The output directory for the generated wrapper code
        hpp_collection_file : str
            The path to save the header collection file to
        overwrite : bool
            Force rewrite of the header collection file, even if unchanged
        hpp_collection : str
            The output string that gets written to the header collection file
        class_dict : Dict[str, CppClassInfo]
            A dictionary of all class info objects
        free_func_dict : Dict[str, CppFreeFunctionInfo]
            A dictionary of all free function info objects
    """

    def __init__(
        self,
        package_info: PackageInfo,
        wrapper_root: str,
        hpp_collection_file: str,
        overwrite: bool = False,
    ):
        self.package_info: PackageInfo = package_info
        self.wrapper_root: str = wrapper_root
        self.hpp_collection_file: str = hpp_collection_file
        self.overwrite: bool = overwrite
        self.hpp_collection: str = ""

        # For convenience, collect all class and free function info into dicts keyed by name
        self.class_dict: Dict[str, CppClassInfo] = {}
        self.free_func_dict: Dict[str, CppFreeFunctionInfo] = {}

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

    def write(self) -> None:
        """Generate the header file output string and write it to file."""
        # Add the top prefix text
        prefix_text = self.package_info.hierarchy_attribute("prefix_text")
        if prefix_text:
            self.hpp_collection += prefix_text + "\n"

        # Add opening header guard
        self.hpp_collection += f"#ifndef {self.package_info.name}_HEADERS_HPP_\n"
        self.hpp_collection += f"#define {self.package_info.name}_HEADERS_HPP_\n"

        self.hpp_collection += "\n// Includes\n"

        seen_files = set()  # Keep track of included files to avoid duplicates

        if self.should_include_all():
            # Include all the headers
            for filepath in self.package_info.source_hpp_files:
                filename = os.path.basename(filepath)
                if filename not in seen_files:
                    self.hpp_collection += f'#include "{filename}"\n'
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
                        self.hpp_collection += f'#include "{filename}"\n'
                        seen_files.add(filename)

                # Include specific headers needed by free functions
                for free_function_info in module_info.free_function_collection:
                    if free_function_info.source_file_path:
                        filename = os.path.basename(free_function_info.source_file_path)
                        if filename not in seen_files:
                            self.hpp_collection += f'#include "{filename}"\n'
                            seen_files.add(filename)

        # Add the template instantiations e.g. `template class Foo<2,2>;`
        # and typdefs e.g. `typedef Foo<2,2> Foo_2_2;`
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

        self.hpp_collection += "\n// Instantiate Template Classes\n"
        self.hpp_collection += template_instantiations

        self.hpp_collection += "\n// Typedefs for nicer naming\n"
        self.hpp_collection += "namespace cppwg\n{\n"
        self.hpp_collection += template_typedefs
        self.hpp_collection += "} // namespace cppwg\n"

        # Add closing header guard
        self.hpp_collection += f"\n#endif // {self.package_info.name}_HEADERS_HPP_\n"

        # Write the header collection string to file
        write_file_if_changed(
            self.hpp_collection_file, self.hpp_collection, self.overwrite
        )
