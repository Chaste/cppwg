"""Wrapper code writer for C++ classes."""

import logging
import os
from typing import Dict, List

from pygccxml import declarations
from pygccxml.declarations.calldef_members import member_function_t
from pygccxml.declarations.class_declaration import class_t

from cppwg.input.class_info import CppClassInfo
from cppwg.utils.constants import (
    CPPWG_CLASS_OVERRIDE_SUFFIX,
    CPPWG_EXT,
    CPPWG_HEADER_COLLECTION_FILENAME,
)
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
    exposed_class_full_names : List[str]
        A list of full names for all classes in the module
    class_full_names : List[str]
        A list of full names for this class e.g. ["Foo<2,2>", "Foo<3,3>"]
    class_short_names : List[str]
        A list of short names for this class e.g. ["Foo2_2", "Foo3_3"]
    class_decls : List[class_t]
        A list of class declarations associated with the class
    has_shared_ptr : bool
        Whether the class uses shared pointers
    is_abstract : bool
        Whether the class is abstract
    hpp_string : str
        The hpp wrapper code
    cpp_string : str
        The cpp wrapper code
    """

    def __init__(
        self,
        class_info: CppClassInfo,
        wrapper_templates: Dict[str, str],
        exposed_class_full_names: List[str],
    ) -> None:
        logger = logging.getLogger()

        super(CppClassWrapperWriter, self).__init__(wrapper_templates)

        self.class_info: CppClassInfo = class_info

        # Class full names eg. ["Foo<2,2>", "Foo<3,3>"]
        self.class_full_names: List[str] = self.class_info.get_full_names()

        # Class short names eg. ["Foo2_2", "Foo3_3"]
        self.class_short_names: List[str] = self.class_info.get_short_names()

        if len(self.class_full_names) != len(self.class_short_names):
            logger.error("Full and short name lists should be the same length")
            raise AssertionError()

        self.exposed_class_full_names: List[str] = exposed_class_full_names

        self.class_decls: List[class_t] = []
        self.has_shared_ptr: bool = True
        self.is_abstract: bool = False  # TODO: Consider removing unused attribute

        self.hpp_string: str = ""
        self.cpp_string: str = ""

    def add_hpp(self, class_short_name: str) -> None:
        """
        Fill the class hpp string for a single class using the wrapper template.

        Parameters
        ----------
        class_short_name: str
            The short name of the class e.g. Foo2_2
        """
        class_hpp_dict = {"class_short_name": class_short_name}

        self.hpp_string += self.wrapper_templates["class_hpp_header"].format(
            **class_hpp_dict
        )

    def add_cpp_header(self, class_full_name: str, class_short_name: str) -> None:
        """
        Add the 'top' of the class wrapper cpp file for a single class.

        Parameters
        ----------
        class_full_name : str
            The full name of the class e.g. Foo<2,2>
        class_short_name : str
            The short name of the class e.g. Foo2_2
        """
        # Add the includes for this class
        includes = ""

        if self.class_info.hierarchy_attribute("common_include_file"):
            includes += f'#include "{CPPWG_HEADER_COLLECTION_FILENAME}"\n'

        else:
            source_includes = self.class_info.hierarchy_attribute_gather(
                "source_includes"
            )

            for source_include in source_includes:
                if source_include[0] == "<":
                    # e.g. #include <string>
                    includes += f"#include {source_include}\n"
                else:
                    # e.g. #include "Foo.hpp"
                    includes += f'#include "{source_include}"\n'

            source_file = self.class_info.source_file
            if not source_file:
                source_file = os.path.basename(self.class_info.decl.location.file_name)
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
            "class_short_name": class_short_name,
            "class_full_name": class_full_name,
            "smart_ptr_handle": smart_ptr_handle,
        }

        self.cpp_string += self.wrapper_templates["class_cpp_header"].format(
            **header_dict
        )

        # Add any specified custom prefix code
        for code_line in self.class_info.prefix_code:
            self.cpp_string += code_line + "\n"

        # Run any custom generators to add additional prefix code
        if self.class_info.custom_generator:
            self.cpp_string += self.class_info.custom_generator.get_class_cpp_pre_code(
                class_short_name
            )

    def add_virtual_overrides(
        self, class_decl: class_t, short_class_name: str
    ) -> List[member_function_t]:
        """
        Add virtual "trampoline" overrides for the class.

        Identify any methods needing overrides (i.e. any that are virtual in the
        current class or in a parent), and add the overrides to the cpp string.

        Parameters
        ----------
        class_decl : class_t
            The class declaration
        short_class_name : str
            The short name of the class e.g. Foo2_2

        Returns
        -------
        list[member_function_t]: A list of member functions needing override
        """
        methods_needing_override: List[member_function_t] = []
        return_types: List[str] = []  # e.g. ["void", "unsigned int", "::Bar<2> *"]

        # Collect all virtual methods and their return types
        for member_function in class_decl.member_functions(allow_empty=True):
            is_pure_virtual = member_function.virtuality == "pure virtual"
            is_virtual = member_function.virtuality == "virtual"
            if is_pure_virtual or is_virtual:
                methods_needing_override.append(member_function)
                return_types.append(member_function.return_type.decl_string)
            if is_pure_virtual:
                self.is_abstract = True

        # Add typedefs for return types with special characters
        # e.g. typedef ::Bar<2> * _Bar_lt_2_gt_Ptr;
        for return_type in return_types:
            if return_type != self.tidy_name(return_type):
                typedef_template = "typedef {full_name} {tidy_name};\n"
                typedef_dict = {
                    "full_name": return_type,
                    "tidy_name": self.tidy_name(return_type),
                }
                self.cpp_string += typedef_template.format(**typedef_dict)
        self.cpp_string += "\n"

        # Override virtual methods
        if methods_needing_override:
            # Add virtual override class, e.g.:
            #   class Foo_Overrides : public Foo {
            #       public:
            #       using Foo::Foo;
            override_header_dict = {
                "class_short_name": short_class_name,
                "class_base_name": self.class_info.name,
            }

            self.cpp_string += self.wrapper_templates[
                "class_virtual_override_header"
            ].format(**override_header_dict)

            # Override each method, e.g.:
            #   void bar(double d) const override {
            #       PYBIND11_OVERRIDE_PURE(
            #           bar,
            #           Foo2_2,
            #           bar,
            #           d);
            #   }
            for method in methods_needing_override:
                method_writer = CppMethodWrapperWriter(
                    self.class_info,
                    method,
                    class_decl,
                    self.wrapper_templates,
                    short_class_name,
                )
                self.cpp_string += method_writer.generate_virtual_override_wrapper()

            self.cpp_string += "\n};\n"

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

        if len(self.class_decls) != len(self.class_full_names):
            logger.error("Not enough class decls added to do write.")
            raise AssertionError()

        for idx, full_name in enumerate(self.class_full_names):
            short_name = self.class_short_names[idx]
            class_decl = self.class_decls[idx]
            self.hpp_string = ""
            self.cpp_string = ""

            # Add the cpp file header
            self.add_cpp_header(full_name, short_name)

            # Check for struct-enum pattern. For example:
            #   struct Foo{
            #     enum Value{A, B, C};
            #   };
            # TODO: Consider moving some parts into templates
            if declarations.is_struct(class_decl):
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
                    self.add_hpp(short_name)

                    # Write the struct cpp and hpp files
                    self.write_files(work_dir, short_name)
                continue

            # Find and define virtual function "trampoline" overrides
            methods_needing_override: List[member_function_t] = (
                self.add_virtual_overrides(class_decl, short_name)
            )

            # Add the virtual "trampoline" overrides from "Foo_Overrides" to
            # the "Foo" wrapper class definition if needed
            # e.g. py::class_<Foo, Foo_Overrides >(m, "Foo")
            overrides_string = ""
            if methods_needing_override:
                overrides_string = f", {short_name}{CPPWG_CLASS_OVERRIDE_SUFFIX}"

            # Add smart pointer support to the wrapper class definition if needed
            # e.g. py::class_<Foo, boost::shared_ptr<Foo > >(m, "Foo")
            smart_ptr_type: str = self.class_info.hierarchy_attribute("smart_ptr_type")
            ptr_support = ""
            if self.has_shared_ptr and smart_ptr_type:
                ptr_support = f", {smart_ptr_type}<{short_name} > "

            # Add base classes to the wrapper class definition if needed
            # e.g. py::class_<Foo, AbstractFoo, InterfaceFoo >(m, "Foo")
            bases = ""

            for base in class_decl.bases:  # type(base) -> hierarchy_info_t
                # Check that the base class is not private
                if base.access_type == "private":
                    continue

                # Check if the base class is exposed (i.e. to be wrapped in the module)
                base_class_name: str = base.related_class.name.replace(" ", "")
                if base_class_name in self.exposed_class_full_names:
                    bases += f", {base.related_class.name} "

            # Add the class registration
            class_definition_dict = {
                "short_name": short_name,
                "overrides_string": overrides_string,
                "ptr_support": ptr_support,
                "bases": bases,
            }
            class_definition_template = self.wrapper_templates["class_definition"]
            self.cpp_string += class_definition_template.format(**class_definition_dict)

            # Add public constructors
            query = declarations.access_type_matcher_t("public")
            for constructor in class_decl.constructors(
                function=query, allow_empty=True
            ):
                constructor_writer = CppConstructorWrapperWriter(
                    self.class_info,
                    constructor,
                    class_decl,
                    self.wrapper_templates,
                    short_name,
                )
                self.cpp_string += constructor_writer.generate_wrapper()

            # Add public member functions
            query = declarations.access_type_matcher_t("public")
            for member_function in class_decl.member_functions(
                function=query, allow_empty=True
            ):
                if self.class_info.excluded_methods:
                    # Skip excluded methods
                    if member_function.name in self.class_info.excluded_methods:
                        continue

                method_writer = CppMethodWrapperWriter(
                    self.class_info,
                    member_function,
                    class_decl,
                    self.wrapper_templates,
                    short_name,
                )
                self.cpp_string += method_writer.generate_wrapper()

            # Run any custom generators to add additional class code
            if self.class_info.custom_generator:
                self.cpp_string += (
                    self.class_info.custom_generator.get_class_cpp_def_code(short_name)
                )

            # Close the class definition
            self.cpp_string += "    ;\n}\n"

            # Set up the hpp
            self.add_hpp(short_name)

            # Write the class cpp and hpp files
            self.write_files(work_dir, short_name)

    def write_files(self, work_dir: str, class_short_name: str) -> None:
        """
        Write the hpp and cpp wrapper code to file.

        Parameters
        ----------
            work_dir : str
                The directory to write the files to
            class_short_name : str
                The short name of the class e.g. Foo2_2
        """
        hpp_filepath = os.path.join(work_dir, f"{class_short_name}.{CPPWG_EXT}.hpp")
        cpp_filepath = os.path.join(work_dir, f"{class_short_name}.{CPPWG_EXT}.cpp")

        with open(hpp_filepath, "w") as hpp_file:
            hpp_file.write(self.hpp_string)

        with open(cpp_filepath, "w") as cpp_file:
            cpp_file.write(self.cpp_string)
