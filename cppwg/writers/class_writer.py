"""Wrapper code writer for C++ classes."""

import logging
import os
from typing import Dict, List

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


class CppClassWrapperWriter(CppBaseWrapperWriter):
    """
    Writer to generate wrapper code for C++ classes.

    Attributes
    ----------
    class_info : CppClassInfo
        The class information
    wrapper_templates : Dict[str, str]
        String templates with placeholders for generating wrapper code
    module_classes : Dict[pygccxml.declarations.class_t, str]
        A dictionary of decls and names for all classes in the module
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
        class_info: "CppClassInfo",  # noqa: F821
        wrapper_templates: Dict[str, str],
        module_classes: Dict["class_t", str],  # noqa: F821
        overwrite: bool = False,
    ) -> None:
        logger = logging.getLogger()

        super().__init__(wrapper_templates)

        self.class_info = class_info

        if len(self.class_info.cpp_names) != len(self.class_info.py_names):
            logger.error("C++ and Python class name lists should be the same length")
            raise AssertionError()

        self.module_classes = module_classes

        self.overwrite = overwrite

        self.has_shared_ptr: bool = True

        self.hpp_string: str = ""
        self.cpp_string: str = ""

    def add_hpp(self, class_py_name: str) -> None:
        """
        Fill the class hpp string for a single class using the wrapper template.

        Parameters
        ----------
        class_py_name: str
            The Python name of the class e.g. Foo_2_2
        """
        # Add the top prefix text
        prefix_text = self.class_info.hierarchy_attribute("prefix_text")
        if prefix_text:
            self.hpp_string += prefix_text + "\n"

        # Add the header guard, includes and declarations
        class_hpp_dict = {"class_py_name": class_py_name}

        self.hpp_string += self.wrapper_templates["class_hpp_header"].format(
            **class_hpp_dict
        )

    def add_cpp_header(self, class_cpp_name: str, class_py_name: str) -> None:
        """
        Add the 'top' of the class wrapper cpp file for a single class.

        Parameters
        ----------
        class_cpp_name : str
            The C++ name of the class e.g. Foo<2,2>
        class_py_name : str
            The Python name of the class e.g. Foo_2_2
        """
        # Add the top prefix text
        prefix_text = self.class_info.hierarchy_attribute("prefix_text")
        if prefix_text:
            self.cpp_string += prefix_text + "\n"

        # Add the includes for this class
        includes = ""

        if self.class_info.hierarchy_attribute("common_include_file"):
            includes += f'#include "{CPPWG_HEADER_COLLECTION_FILENAME}"\n'

        else:
            source_includes = [
                inc
                for inc_list in self.class_info.hierarchy_attribute_gather(
                    "source_includes"
                )
                for inc in inc_list
            ]

            for source_include in source_includes:
                if source_include[0] == "<":
                    # e.g. #include <string>
                    includes += f"#include {source_include}\n"
                else:
                    # e.g. #include "Foo.hpp"
                    includes += f'#include "{source_include}"\n'

            source_file = self.class_info.source_file
            if not source_file:
                source_file = os.path.basename(
                    self.class_info.decls[0].location.file_name
                )
            includes += f'#include "{source_file}"\n'

        # Check for custom smart pointers e.g. "boost::shared_ptr"
        smart_ptr_type: str = self.class_info.hierarchy_attribute("smart_ptr_type")

        smart_ptr_handle = ""
        if smart_ptr_type:
            # Adds e.g. "PYBIND11_DECLARE_HOLDER_TYPE(T, boost::shared_ptr<T>)"
            smart_ptr_handle = self.wrapper_templates["smart_pointer_holder"].format(
                smart_ptr_type
            )

        # Fill in the cpp header template
        header_dict = {
            "includes": includes,
            "class_py_name": class_py_name,
            "class_cpp_name": class_cpp_name,
            "smart_ptr_handle": smart_ptr_handle,
        }

        self.cpp_string += self.wrapper_templates["class_cpp_header"].format(
            **header_dict
        )

        # Add any specified custom prefix code
        for code_line in self.class_info.prefix_code:
            self.cpp_string += code_line + "\n"

        # Run any custom generators to add additional prefix code
        generator = self.class_info.custom_generator_instance
        if generator:
            self.cpp_string += generator.get_class_cpp_pre_code(class_py_name)

    def add_virtual_overrides(
        self, template_idx: int
    ) -> List["member_function_t"]:  # noqa: F821
        """
        Add virtual "trampoline" overrides for the class.

        Identify any methods needing overrides (i.e. any that are virtual in the
        current class or in a base class), and add the overrides to the cpp string.

        Parameters
        ----------
        template_idx : int
            The index of the template in the class info

        Returns
        -------
        list[pygccxml.declarations.member_function_t]: A list of member functions needing override
        """
        methods_needing_override: List["member_function_t"] = []  # noqa: F821
        return_types: List[str] = []  # e.g. ["void", "unsigned int", "::Bar<2> *"]

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
        for return_type in return_types:
            if return_type != self.tidy_name(return_type):
                typedef_template = "typedef {class_cpp_name} {tidy_name};\n"
                typedef_dict = {
                    "class_cpp_name": return_type,
                    "tidy_name": self.tidy_name(return_type),
                }
                self.cpp_string += typedef_template.format(**typedef_dict)
        self.cpp_string += "\n"

        # Override virtual methods
        class_py_name = self.class_info.py_names[template_idx]
        if methods_needing_override:
            # Add virtual override class, e.g.:
            #   class Foo_Overrides : public Foo {
            #       public:
            #       using Foo::Foo;
            override_header_dict = {
                "class_py_name": class_py_name,
                "class_base_name": self.class_info.name,
            }

            self.cpp_string += self.wrapper_templates[
                "class_virtual_override_header"
            ].format(**override_header_dict)

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
                self.cpp_string += method_writer.generate_virtual_override_wrapper()

            self.cpp_string += "};\n\n"

        return methods_needing_override

    def write(self, work_dir: str) -> None:
        """
        Write the hpp and cpp wrapper codes to file.

        Parameters
        ----------
        work_dir : str
            The directory to write the files to
        """
        logger = logging.getLogger()

        if len(self.class_info.decls) != len(self.class_info.cpp_names):
            logger.error("Not enough class decls added to do write.")
            raise AssertionError()

        for idx, class_cpp_name in enumerate(self.class_info.cpp_names):
            class_py_name = self.class_info.py_names[idx]
            class_decl = self.class_info.decls[idx]
            self.hpp_string = ""
            self.cpp_string = ""

            # Add the cpp file header
            self.add_cpp_header(class_cpp_name, class_py_name)

            # Check for struct-enum pattern. For example:
            #   struct Foo{
            #     enum Value{A, B, C};
            #   };
            if type_traits_classes.is_struct(class_decl):
                enums = class_decl.enumerations(allow_empty=True)

                if len(enums) == 1:
                    enum_tpl = "void register_{class}_class(py::module &m){{\n"
                    enum_tpl += '    py::class_<{class}> myclass(m, "{class}");\n'
                    enum_tpl += '    py::enum_<{class}::{enum}>(myclass, "{enum}")\n'

                    replacements = {"class": class_decl.name, "enum": enums[0].name}
                    self.cpp_string += enum_tpl.format(**replacements)

                    value_tpl = '        .value("{val}", {class}::{enum}::{val})\n'
                    for value in enums[0].values:
                        replacements["val"] = value[0]
                        self.cpp_string += value_tpl.format(**replacements)

                    self.cpp_string += "    .export_values();\n}\n"

                    # Set up the hpp
                    self.add_hpp(class_py_name)

                    # Write the struct cpp and hpp files
                    self.write_files(work_dir, class_py_name)
                continue

            # Find and define virtual function "trampoline" overrides
            methods_needing_override = self.add_virtual_overrides(idx)

            # Add the virtual "trampoline" overrides from "Foo_Overrides" to
            # the "Foo" wrapper class definition if needed
            # e.g. py::class_<Foo, Foo_Overrides >(m, "Foo")
            overrides_string = ""
            if methods_needing_override:
                overrides_string = f", {class_py_name}{CPPWG_CLASS_OVERRIDE_SUFFIX}"

            # Add smart pointer support to the wrapper class definition if needed
            # e.g. py::class_<Foo, boost::shared_ptr<Foo > >(m, "Foo")
            smart_ptr_type: str = self.class_info.hierarchy_attribute("smart_ptr_type")
            ptr_support = ""
            if self.has_shared_ptr and smart_ptr_type:
                ptr_support = f", {smart_ptr_type}<{class_py_name}>"

            # Add base classes to the wrapper class definition if needed
            # e.g. py::class_<Foo, AbstractFoo, InterfaceFoo >(m, "Foo")
            bases = ""

            for base in class_decl.bases:  # type(base) -> hierarchy_info_t
                # Check that the base class is not private
                if base.access_type == "private":
                    continue

                # Check if the base class is also wrapped in the module
                if base.related_class in self.module_classes:
                    bases += f", {self.module_classes[base.related_class]}"

            # Add the class registration
            class_definition_dict = {
                "class_py_name": class_py_name,
                "overrides_string": overrides_string,
                "ptr_support": ptr_support,
                "bases": bases,
            }
            class_definition_template = self.wrapper_templates["class_definition"]
            self.cpp_string += class_definition_template.format(**class_definition_dict)

            # Add public constructors
            query = access_type_matcher_t("public")
            for constructor in class_decl.constructors(
                function=query, allow_empty=True
            ):
                constructor_writer = CppConstructorWrapperWriter(
                    self.class_info,
                    idx,
                    constructor,
                    self.wrapper_templates,
                )
                self.cpp_string += constructor_writer.generate_wrapper()

            # Add public member functions
            query = access_type_matcher_t("public")
            for member_function in class_decl.member_functions(
                function=query, allow_empty=True
            ):
                method_writer = CppMethodWrapperWriter(
                    self.class_info,
                    idx,
                    member_function,
                    self.wrapper_templates,
                )
                self.cpp_string += method_writer.generate_wrapper()

            # Run any custom generators to add additional class code
            generator = self.class_info.custom_generator_instance
            if generator:
                self.cpp_string += generator.get_class_cpp_def_code(class_py_name)

            # Add any specified custom suffix code
            for code_line in self.class_info.suffix_code:
                self.cpp_string += code_line + "\n"

            # Close the class definition
            self.cpp_string += "    ;\n}\n"

            # Set up the hpp
            self.add_hpp(class_py_name)

            # Write the class cpp and hpp files
            self.write_files(work_dir, class_py_name)

    def write_files(self, work_dir: str, class_py_name: str) -> None:
        """
        Write the hpp and cpp wrapper code to file.

        Parameters
        ----------
            work_dir : str
                The directory to write the files to
            class_py_name : str
                The Python name of the class e.g. Foo_2_2
        """
        hpp_filepath = os.path.join(work_dir, f"{class_py_name}.{CPPWG_EXT}.hpp")
        cpp_filepath = os.path.join(work_dir, f"{class_py_name}.{CPPWG_EXT}.cpp")

        write_file_if_changed(hpp_filepath, self.hpp_string, self.overwrite)
        write_file_if_changed(cpp_filepath, self.cpp_string, self.overwrite)
