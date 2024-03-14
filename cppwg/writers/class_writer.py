import os
import logging

from pygccxml import declarations
from pygccxml.declarations.calldef_members import member_function_t
from pygccxml.declarations.class_declaration import class_t

from cppwg.input.class_info import CppClassInfo

from cppwg.writers.base_writer import CppBaseWrapperWriter
from cppwg.writers.method_writer import CppMethodWrapperWriter
from cppwg.writers.constructor_writer import CppConstructorWrapperWriter

from cppwg.utils.constants import CPPWG_EXT


class CppClassWrapperWriter(CppBaseWrapperWriter):
    """
    This class generates wrapper code for C++ classes

    Attributes
    ----------
    class_info : CppClassInfo
        The class information
    wrapper_templates : dict[str, str]
        String templates with placeholders for generating wrapper code
    exposed_class_full_names : list[str]
        A list of full names for all classes in the module
    class_full_names : list[str]
        A list of full names for this class e.g. ["Foo<2,2>", "Foo<3,3>"]
    class_short_names : list[str]
        A list of short names for this class e.g. ["Foo2_2", "Foo3_3"]
    class_decls : list[class_t]
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
        wrapper_templates: dict[str, str],
        exposed_class_full_names: list[str],
    ):
        logger = logging.getLogger()

        super(CppClassWrapperWriter, self).__init__(wrapper_templates)

        self.class_info: CppClassInfo = class_info

        # Class full names eg. ["Foo<2,2>", "Foo<3,3>"]
        self.class_full_names: list[str] = self.class_info.get_full_names()

        # Class short names eg. ["Foo2_2", "Foo3_3"]
        self.class_short_names: list[str] = self.class_info.get_short_names()

        if len(self.class_full_names) != len(self.class_short_names):
            logger.error("Full and short name lists should be the same length")
            raise AssertionError()

        self.exposed_class_full_names: list[str] = exposed_class_full_names

        self.class_decls: list[class_t] = []
        self.has_shared_ptr: bool = True
        self.is_abstract: bool = False

        self.hpp_string: str = ""
        self.cpp_string: str = ""

    def add_hpp(self, class_short_name: str) -> None:
        """
        Fill the class hpp string from the wrapper template

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
        Add the 'top' of the class wrapper cpp file

        Parameters
        ----------
        class_full_name : str
            The full name of the class e.g. Foo<2,2>
        class_short_name : str
            The short name of the class e.g. Foo2_2
        """

        header = "wrapper_header_collection"

        # Check for custom smart pointers
        smart_ptr_handle = ""
        smart_pointer_handle = self.class_info.hierarchy_attribute("smart_ptr_type")
        if smart_pointer_handle != None:
            smart_ptr_template = self.wrapper_templates["smart_pointer_holder"]
            smart_ptr_handle = (
                "\n" + smart_ptr_template.format(smart_pointer_handle) + ";"
            )

        header_dict = {
            "wrapper_header_collection": header,
            "class_short_name": class_short_name,
            "class_full_name": class_full_name,
            "smart_ptr_handle": smart_ptr_handle,
            "includes": '#include "' + header + '.hpp"\n',
        }
        extra_include_string = ""
        common_include_file = self.class_info.hierarchy_attribute("common_include_file")

        source_includes = self.class_info.hierarchy_attribute_gather("source_includes")

        if not common_include_file:
            for eachInclude in source_includes:
                if eachInclude[0] != "<":
                    extra_include_string += '#include "' + eachInclude + '"\n'
                else:
                    extra_include_string += "#include " + eachInclude + "\n"
            if self.class_info.source_file is not None:
                extra_include_string += (
                    '#include "' + self.class_info.source_file + '"\n'
                )
            else:
                include_name = os.path.basename(self.class_info.decl.location.file_name)
                extra_include_string += '#include "' + include_name + '"\n'
            header_dict["includes"] = extra_include_string

        header_string = self.wrapper_templates["class_cpp_header"].format(**header_dict)
        self.cpp_string += header_string

        for eachLine in self.class_info.prefix_code:
            self.cpp_string += eachLine + "\n"

        # Any custom generators
        if self.class_info.custom_generator is not None:
            self.cpp_string += self.class_info.custom_generator.get_class_cpp_pre_code(
                class_short_name
            )

    def add_virtual_overrides(
        self, class_decl: class_t, short_class_name: str
    ) -> list[member_function_t]:
        """
        Virtual overrides if neeeded

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

        # Identify any methods needing over-rides, i.e. any that are virtual
        # here or in a parent.
        methods_needing_override = []
        return_types = []
        for member_function in class_decl.member_functions(allow_empty=True):
            is_pure_virtual = member_function.virtuality == "pure virtual"
            is_virtual = member_function.virtuality == "virtual"
            if is_pure_virtual or is_virtual:
                methods_needing_override.append(member_function)
                return_types.append(member_function.return_type.decl_string)
            if is_pure_virtual:
                self.is_abstract = True

        for eachReturnString in return_types:
            if eachReturnString != self.tidy_name(eachReturnString):
                typdef_string = "typedef {full_name} {tidy_name};\n"
                typdef_dict = {
                    "full_name": eachReturnString,
                    "tidy_name": self.tidy_name(eachReturnString),
                }
                self.cpp_string += typdef_string.format(**typdef_dict)
        self.cpp_string += "\n"

        needs_override = len(methods_needing_override) > 0
        if needs_override:
            over_ride_dict = {
                "class_short_name": short_class_name,
                "class_base_name": self.class_info.name,
            }
            override_template = self.wrapper_templates["class_virtual_override_header"]
            self.cpp_string += override_template.format(**over_ride_dict)

            for eachMethod in methods_needing_override:
                writer = CppMethodWrapperWriter(
                    self.class_info,
                    eachMethod,
                    class_decl,
                    self.wrapper_templates,
                    short_class_name,
                )
                self.cpp_string = writer.add_override(self.cpp_string)
            self.cpp_string += "\n};\n"

        return methods_needing_override

    def write(self, work_dir: str) -> None:
        """
        Write the hpp and cpp wrapper codes to file

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

            # Check for struct-enum pattern
            if declarations.is_struct(class_decl):
                enums = class_decl.enumerations(allow_empty=True)
                if len(enums) == 1:
                    replacements = {"class": class_decl.name, "enum": enums[0].name}
                    self.cpp_string += (
                        "void register_{class}_class(py::module &m){{\n".format(
                            **replacements
                        )
                    )
                    self.cpp_string += (
                        '    py::class_<{class}> myclass(m, "{class}");\n'.format(
                            **replacements
                        )
                    )
                    self.cpp_string += (
                        '    py::enum_<{class}::{enum}>(myclass, "{enum}")\n'.format(
                            **replacements
                        )
                    )
                    for eachval in enums[0].values:
                        replacements = {
                            "class": class_decl.name,
                            "enum": enums[0].name,
                            "val": eachval[0],
                        }
                        self.cpp_string += (
                            '        .value("{val}", {class}::{enum}::{val})\n'.format(
                                **replacements
                            )
                        )
                    self.cpp_string += "    .export_values();\n}\n"

                    # Set up the hpp
                    self.add_hpp(short_name)

                    # Do the write
                    self.write_files(work_dir, short_name)
                continue

            # Define any virtual function overloads
            methods_needing_override = self.add_virtual_overrides(
                class_decl, short_name
            )

            # Add overrides if needed
            overrides_string = ""
            if len(methods_needing_override) > 0:
                overrides_string = ", " + short_name + "_Overloads"

            # Add smart ptr support if needed
            smart_pointer_handle = self.class_info.hierarchy_attribute("smart_ptr_type")
            ptr_support = ""
            if self.has_shared_ptr and smart_pointer_handle is not None:
                ptr_support = ", " + smart_pointer_handle + "<" + short_name + " > "

            # Add base classes if needed
            bases = ""
            for base in class_decl.bases:
                cleaned_base = base.related_class.name.replace(" ", "")
                exposed = any(
                    cleaned_base in t.replace(" ", "")
                    for t in self.exposed_class_full_names
                )
                public = not base.access_type == "private"
                if exposed and public:
                    bases += ", " + base.related_class.name + " "

            # Add the class registration
            class_definition_dict = {
                "short_name": short_name,
                "overrides_string": overrides_string,
                "ptr_support": ptr_support,
                "bases": bases,
            }
            class_definition_template = self.wrapper_templates["class_definition"]
            self.cpp_string += class_definition_template.format(**class_definition_dict)

            # Add constructors
            # if not self.is_abstract and not class_decl.is_abstract:
            # No constructors for classes with private pure virtual methods!

            ppv_class = False
            for member_function in class_decl.member_functions(allow_empty=True):
                if (
                    member_function.virtuality == "pure virtual"
                    and member_function.access_type == "private"
                ):
                    ppv_class = True
                    break

            if not ppv_class:
                query = declarations.access_type_matcher_t("public")
                for constructor in class_decl.constructors(
                    function=query, allow_empty=True
                ):
                    writer = CppConstructorWrapperWriter(
                        self.class_info,
                        constructor,
                        class_decl,
                        self.wrapper_templates,
                        short_name,
                    )
                    # TODO: Consider returning the constructor string instead
                    self.cpp_string = writer.add_self(self.cpp_string)

            # Add public member functions
            query = declarations.access_type_matcher_t("public")
            for member_function in class_decl.member_functions(
                function=query, allow_empty=True
            ):
                excluded = False
                if self.class_info.excluded_methods is not None:
                    excluded = member_function.name in self.class_info.excluded_methods
                if not excluded:
                    writer = CppMethodWrapperWriter(
                        self.class_info,
                        member_function,
                        class_decl,
                        self.wrapper_templates,
                        short_name,
                    )
                    # TODO: Consider returning the member string instead
                    self.cpp_string = writer.add_self(self.cpp_string)

            # Any custom generators
            if self.class_info.custom_generator is not None:
                self.cpp_string += (
                    self.class_info.custom_generator.get_class_cpp_def_code(short_name)
                )

            # Close the class definition
            self.cpp_string += "    ;\n}\n"

            # Set up the hpp
            self.add_hpp(short_name)

            # Do the write
            self.write_files(work_dir, short_name)

    def write_files(self, work_dir: str, class_short_name: str) -> None:
        """
        Write the hpp and cpp wrapper code to file

        Parameters
        ----------
            work_dir : str
                The directory to write the files to
            class_short_name : str
                The short name of the class
        """

        hpp_filepath = os.path.join(work_dir, f"{class_short_name}.{CPPWG_EXT}.hpp")
        cpp_filepath = os.path.join(work_dir, f"{class_short_name}.{CPPWG_EXT}.cpp")

        with open(hpp_filepath, "w") as hpp_file:
            hpp_file.write(self.hpp_string)

        with open(cpp_filepath, "w") as cpp_file:
            cpp_file.write(self.cpp_string)
