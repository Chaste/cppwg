import logging

from pathlib import Path
from typing import Optional

from pygccxml import parser, declarations

from pygccxml.declarations import declaration_t

# declaration_t is the base type for all declarations in pygccxml including:
# - class_declaration_t (pygccxml.declarations.class_declaration.class_declaration_t)
# - class_t (pygccxml.declarations.class_declaration.class_t)
# - constructor_t (pygccxml.declarations.calldef_members.constructor_t)
# - destructor_t (pygccxml.declarations.calldef_members.destructor_t)
# - free_function_t (pygccxml.declarations.free_calldef.free_function_t)
# - free_operator_t (pygccxml.declarations.free_calldef.free_operator_t)
# - member_function_t (pygccxml.declarations.calldef_members.member_function_t)
# - member_operator_t (pygccxml.declarations.calldef_members.member_operator_t)
# - typedef_t (pygccxml.declarations.typedef.typedef_t)
# - variable_t (pygccxml.declarations.variable.variable_t)

from pygccxml.declarations.mdecl_wrapper import mdecl_wrapper_t
from pygccxml.declarations.namespace import namespace_t


class CppSourceParser:
    """
    Parser for C++ source code

    Attributes
    ----------
        source_root : str
            The root directory of the source code
        wrapper_header_collection : str
            The path to the header collection file
        castxml_binary : str
            The path to the CastXML binary
        source_includes : list[str]
            The list of source include paths
        castxml_cflags : str
            Optional cflags to be passed to CastXML e.g. "-std=c++17"
        global_ns : namespace_t
            The namespace containing all parsed C++ declarations
        source_ns : namespace_t
            The namespace containing C++ declarations from the source tree
    """

    def __init__(
        self,
        source_root: str,
        wrapper_header_collection: str,
        castxml_binary: str,
        source_includes: list[str],
        castxml_cflags: str = "",
    ):
        self.source_root: str = source_root
        self.wrapper_header_collection: str = wrapper_header_collection
        self.castxml_binary: str = castxml_binary
        self.source_includes: list[str] = source_includes
        self.castxml_cflags: str = castxml_cflags

        self.source_ns: Optional[namespace_t] = None
        self.global_ns: Optional[namespace_t] = None

    def parse(self) -> namespace_t:
        """
        Parses C++ source code from the header collection using CastXML and pygccxml.

        Returns
        -------
        namespace_t
            The namespace containing C++ declarations from the source tree
        """
        logger = logging.getLogger()

        # Configure the XML generator (CastXML)
        xml_generator_config = parser.xml_generator_configuration_t(
            xml_generator_path=self.castxml_binary,
            xml_generator="castxml",
            cflags=self.castxml_cflags,
            include_paths=self.source_includes,
        )

        # Parse all the C++ source code to extract declarations
        logger.info("Parsing source code for declarations.")
        decls: list[declaration_t] = parser.parse(
            files=[self.wrapper_header_collection],
            config=xml_generator_config,
            compilation_mode=parser.COMPILATION_MODE.ALL_AT_ONCE,
        )

        # Get access to the global namespace
        self.global_ns: namespace_t = declarations.get_global_namespace(decls)

        # Filter declarations for which files exist
        logger.info("Filtering source declarations.")
        query = declarations.custom_matcher_t(lambda decl: decl.location is not None)
        filtered_decls: mdecl_wrapper_t = self.global_ns.decls(function=query)

        # Filter declarations in our source tree; include declarations from the
        # wrapper_header_collection file for explicit instantiations, typedefs etc.
        source_decls: list[declaration_t] = [
            decl
            for decl in filtered_decls
            if Path(self.source_root) in Path(decl.location.file_name).parents
            or decl.location.file_name == self.wrapper_header_collection
        ]

        # Create a source namespace module for the filtered declarations
        self.source_ns = namespace_t(name="source", declarations=source_decls)

        # Initialise the source namespace's internal type hash tables for faster queries
        logger.info("Optimizing source declaration queries.")
        self.source_ns.init_optimizer()

        return self.source_ns
