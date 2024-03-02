from typing import Optional

from pygccxml import parser, declarations

# declaration_t is the base type for all declarations in pygccxml including:
# - class_declaration_t (pygccxml.declarations.class_declaration.class_declaration_t)
# - class_t (pygccxml.declarations.class_declaration)
# - constructor_t (pygccxml.declarations.calldef_members.constructor_t)
# - free_function_t (pygccxml.declarations.free_calldef.free_function_t)
# - free_operator_t (pygccxml.declarations.free_calldef.free_operator_t)
# - destructor_t (pygccxml.declarations.calldef_members.destructor_t)
# - member_function_t (pygccxml.declarations.calldef_members.member_function_t)
# - member_operator_t (pygccxml.declarations.calldef_members.member_operator_t)
# - typedef_t (pygccxml.declarations.typedef.typedef_t)
# - variable_t (pygccxml.declarations.variable.variable_t)
from pygccxml.declarations import declaration_t

from pygccxml.declarations.matchers import custom_matcher_t
from pygccxml.declarations.mdecl_wrapper import mdecl_wrapper_t
from pygccxml.declarations.namespace import namespace_t

from pygccxml.parser.config import xml_generator_configuration_t


class CppSourceParser:

    def __init__(
        self,
        source_root: str,
        wrapper_header_collection: str,
        castxml_binary: str,
        source_includes: list[str],
        cflags: str = "",
    ):
        self.source_root: str = source_root
        self.wrapper_header_collection: str = wrapper_header_collection
        self.castxml_binary: str = castxml_binary
        self.source_includes: list[str] = source_includes
        self.cflags: str = cflags
        self.source_ns: Optional[namespace_t] = None

    def parse(self):
        """
        Parses the C++ source code using CastXML and pygccxml from the
        information given in a single header collection file.

        Args:
            source_root (str): The root directory of the source code
            wrapper_header_collection (str): The path to the header collection file
            castxml_binary (str): The path to the CastXML binary
            source_includes (list[str]): The list of source include paths
            cflags (str, optional): Optional cflags to be passed to CastXML e.g. "-std=c++17".

        Returns:
            namespace_t: The filtered source namespace
        """

        xml_generator_config: xml_generator_configuration_t = (
            xml_generator_configuration_t(
                xml_generator_path=self.castxml_binary,
                xml_generator="castxml",
                cflags=self.cflags,
                include_paths=self.source_includes,
            )
        )

        print("INFO: Parsing Code")
        decls: list[declaration_t] = parser.parse(
            files=[self.wrapper_header_collection],
            config=xml_generator_config,
            compilation_mode=parser.COMPILATION_MODE.ALL_AT_ONCE,
        )

        # Get access to the global namespace
        global_ns: namespace_t = declarations.get_global_namespace(decls)

        # Filter declarations for which files exist
        print("INFO: Cleaning Declarations")
        query: custom_matcher_t = custom_matcher_t(
            lambda decl: decl.location is not None
        )
        clean_decls: mdecl_wrapper_t = global_ns.decls(function=query)

        # Filter declarations in our source tree (+ wrapper_header_collection)
        source_decls: list[declaration_t] = [
            decl
            for decl in clean_decls
            if self.source_root in decl.location.file_name
            or "wrapper_header_collection" in decl.location.file_name
        ]

        # Create a source namespace module for the filtered declarations
        self.source_ns = namespace_t(name="source", declarations=source_decls)

        # Initialise the source namespace's internal type hash tables for faster queries
        print("INFO: Optimizing Declaration Queries")
        self.source_ns.init_optimizer()

        for decl in self.source_ns.decls():
            if str(decl).startswith("AbstractLinear"):
                print(decl)
