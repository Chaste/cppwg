"""Parser for C++ source code."""

import logging
import os
from pathlib import Path

from pygccxml import declarations, parser
from pygccxml.declarations import declaration_t
from pygccxml.declarations.mdecl_wrapper import mdecl_wrapper_t
from pygccxml.declarations.namespace import namespace_t

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


class CppSourceParser:
    """
    Parser for C++ source code.

    Attributes
    ----------
        castxml_cflags : str
            Optional cflags to be passed to CastXML e.g. "-std=c++17"
        castxml_compiler : str
            Optional compiler path to be passed to CastXML
        castxml_binary : str
            The path to the CastXML binary
        source_includes : list[str]
            The list of source include paths
        source_root : str
            The root directory of the source code
        wrapper_header_collection : str
            The path to the header collection file
    """

    def __init__(
        self,
        source_root: str,
        wrapper_header_collection: str,
        castxml_binary: str,
        source_includes: list[str],
        castxml_cflags: str = "",
        castxml_compiler: str = None,
    ):
        self.source_root: str = source_root
        self.wrapper_header_collection: str = wrapper_header_collection
        self.castxml_binary: str = castxml_binary
        self.source_includes: list[str] = source_includes
        self.castxml_cflags: str = castxml_cflags
        self.castxml_compiler: str = castxml_compiler

    def xml_generator_config(self) -> parser.xml_generator_configuration_t:
        """
        Build the CastXML configuration for parsing.

        Returns
        -------
        parser.xml_generator_configuration_t
            The XML generator configuration.
        """
        logger = logging.getLogger()

        xml_generator_config = parser.xml_generator_configuration_t(
            xml_generator_path=self.castxml_binary,
            xml_generator="castxml",
            cflags=self.castxml_cflags,
            compiler_path=self.castxml_compiler,
            include_paths=self.source_includes,
        )
        logger.info(f"Using compiler: {xml_generator_config.compiler_path}")

        return xml_generator_config

    def parse(self) -> namespace_t:
        """
        Parse the C++ source code from the header collection using CastXML and pygccxml.

        Returns
        -------
        namespace_t
            The namespace containing C++ declarations from the source tree
        """
        logger = logging.getLogger()

        # Configure the XML generator (CastXML)
        xml_generator_config = self.xml_generator_config()

        # Parse all the C++ source code to extract declarations
        logger.info("Parsing source code for declarations.")
        decls: list[declaration_t] = parser.parse(
            files=[self.wrapper_header_collection],
            config=xml_generator_config,
            compilation_mode=parser.COMPILATION_MODE.ALL_AT_ONCE,
        )

        # Get access to the global namespace containing all parsed C++ declarations
        global_ns: namespace_t = declarations.get_global_namespace(decls)

        # Filter declarations for which files exist
        logger.info("Filtering source declarations.")
        query = declarations.custom_matcher_t(lambda decl: decl.location is not None)
        filtered_decls: mdecl_wrapper_t = global_ns.decls(function=query)

        # Filter declarations in our source tree; include declarations from the
        # wrapper_header_collection file for explicit instantiations, typedefs etc.
        source_decls: list[declaration_t] = [
            decl
            for decl in filtered_decls
            if Path(self.source_root) in Path(decl.location.file_name).parents
            or decl.location.file_name == self.wrapper_header_collection
        ]

        # Create a source namespace module for the filtered declarations
        source_ns = namespace_t(name="source", declarations=source_decls)

        # Initialise the source namespace's internal type hash tables for faster queries
        logger.info("Optimizing source declaration queries.")
        source_ns.init_optimizer()

        return source_ns

    def parse_instantiations(
        self, source_files: list[str]
    ) -> dict[str, list[list[str]]]:
        """
        Find explicit template instantiations in the given source files.

        CastXML only sees the template definitions in the headers, not the
        explicit instantiations (e.g. `template class Foo<2>;`) that live in the
        implementation files. This parses each implementation file and collects
        the template class instantiations it defines, returning a map of base
        class name to the template argument lists found.

        Only instantiations located in the parsed file itself are kept (i.e. the
        explicit instantiations), not the many implicit instantiations pulled in
        from included headers. Files that fail to parse are skipped with a
        warning, so discovery is best-effort and never fatal to generation.

        Parameters
        ----------
        source_files : list[str]
            The implementation files (typically .cpp) to scan.

        Returns
        -------
        dict[str, list[list[str]]]
            Map of base class name to discovered template arg lists,
            e.g. {"Foo": [["2"], ["3"]], "AbstractMesh": [["2", "2"]]}.
        """
        logger = logging.getLogger()

        xml_generator_config = self.xml_generator_config()

        instantiation_map: dict[str, list[list[str]]] = {}

        for source_file in source_files:
            logger.info(f"Scanning for template instantiations: {source_file}")

            try:
                decls: list[declaration_t] = parser.parse(
                    files=[source_file],
                    config=xml_generator_config,
                    compilation_mode=parser.COMPILATION_MODE.ALL_AT_ONCE,
                )
            except Exception as e:
                logger.warning(
                    f"Could not parse {source_file} for template instantiations: {e}"
                )
                continue

            global_ns: namespace_t = declarations.get_global_namespace(decls)

            for class_decl in global_ns.classes(allow_empty=True):
                # Keep only explicit instantiations defined in this file.
                if class_decl.location is None:
                    continue
                if os.path.realpath(class_decl.location.file_name) != os.path.realpath(
                    source_file
                ):
                    continue

                if not declarations.templates.is_instantiation(class_decl.name):
                    continue

                base, args = declarations.templates.split(class_decl.name)
                arg_lists = instantiation_map.setdefault(base, [])
                if args not in arg_lists:
                    arg_lists.append(args)

        return instantiation_map
