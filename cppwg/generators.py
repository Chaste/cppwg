"""The main interface for generating Python wrappers."""

import logging
import os
import re
import shutil
import subprocess
import uuid

import pygccxml

from cppwg.info.package_info import PackageInfo
from cppwg.parsers.package_info_parser import PackageInfoParser
from cppwg.parsers.source_parser import CppSourceParser
from cppwg.templates import pybind11_default as wrapper_templates
from cppwg.utils import utils
from cppwg.utils.constants import (
    CPPWG_DEFAULT_WRAPPER_DIR,
    CPPWG_HEADER_COLLECTION_FILENAME,
)
from cppwg.version import __version__ as cppwg_version
from cppwg.writers.header_collection_writer import CppHeaderCollectionWriter
from cppwg.writers.package_writer import CppPackageWrapperWriter


class CppWrapperGenerator:
    """
    Main class for generating C++ wrappers.

    Attributes
    ----------
    source_root : str
        The root directory of the C++ source code
    source_includes : list[str]
        The list of source include paths
    wrapper_root : str
        The output directory for the wrapper code
    castxml_binary : str
        The path to the castxml binary
    castxml_cflags : str
        Optional cflags to be passed to castxml e.g. "-std=c++17"
    castxml_compiler : str
        Optional compiler path to be passed to CastXML
    package_info_path : str
        The path to the package info yaml config file; defaults to "package_info.yaml"
    source_ns : pygccxml.declarations.namespace_t
        The namespace containing C++ declarations parsed from the source tree
    package_info : PackageInfo
        A data structure containing the information parsed from package_info_path
    overwrite : bool
        Force rewrite of all wrapper files, even if unchanged; defaults to False
    """

    def __init__(
        self,
        source_root: str,
        source_includes: list[str] | None = None,
        wrapper_root: str | None = None,
        castxml_binary: str | None = None,
        package_info_path: str | None = None,
        castxml_cflags: str | None = None,
        castxml_compiler: str | None = None,
        overwrite: bool = False,
        cache_path: str | None = None,
    ):
        logger = logging.getLogger()

        # Whether to force rewriting wrapper files that are unchanged
        self.overwrite: bool = overwrite

        # Optional path to a pygccxml parse cache reused across runs
        self.cache_path: str | None = cache_path

        logger.info(f"cppwg version {cppwg_version}")

        # Check that castxml_binary exists and is executable
        self.castxml_binary: str = ""

        if castxml_binary:
            if os.path.isfile(castxml_binary) and os.access(castxml_binary, os.X_OK):
                self.castxml_binary = castxml_binary
            else:
                logger.warning(
                    "Could not find specified castxml binary. Searching on path."
                )

        # Search for castxml_binary
        if not self.castxml_binary:
            path_to_castxml, _ = pygccxml.utils.find_xml_generator(name="castxml")

            if path_to_castxml:
                self.castxml_binary = path_to_castxml
                logger.info(f"Found castxml binary: {self.castxml_binary}")
            else:
                logger.error("Could not find a castxml binary.")
                raise FileNotFoundError()

        # Check castxml and pygccxml versions
        castxml_version_output: str = (
            subprocess.check_output([self.castxml_binary, "--version"])
            .decode("ascii")
            .strip()
        )
        version_match = re.search(
            r"castxml version (\d+)\.(\d+)\.(\d+)", castxml_version_output
        )
        logger.info(version_match.group(0))
        logger.info(f"pygccxml version {pygccxml.__version__}")

        # CastXML 0.6.0 onwards keeps defaulted trailing template arguments in an
        # instantiation's name (e.g. "AbstractMesh<2, 2>"); earlier versions drop
        # them ("AbstractMesh<2>"). Discovery reads args from source text to be
        # independent of this, but the CastXML fallback (for macro instantiations)
        # can only be safely merged with text-discovered args when its rendering
        # of defaulted args is trustworthy.
        castxml_version = tuple(int(part) for part in version_match.groups())
        self.castxml_keeps_defaulted_args: bool = castxml_version >= (0, 6, 0)

        # Sanitize castxml_cflags
        self.castxml_cflags = "-w"
        if castxml_cflags:
            self.castxml_cflags = f"{self.castxml_cflags} {castxml_cflags}"

        # Try to set castxml compiler
        if castxml_compiler:
            self.castxml_compiler = castxml_compiler
        else:
            compiler_path = shutil.which("clang++")
            if compiler_path:
                self.castxml_compiler = compiler_path
            else:
                self.castxml_compiler = None

        # Sanitize source_root
        self.source_root: str = os.path.abspath(source_root)
        if not os.path.isdir(self.source_root):
            logger.error(f"Could not find source root directory: {source_root}")
            raise FileNotFoundError()

        # Sanitize wrapper_root
        self.wrapper_root: str = ""

        if wrapper_root:
            self.wrapper_root = os.path.abspath(wrapper_root)

        else:
            wrapper_dirname = CPPWG_DEFAULT_WRAPPER_DIR + "_" + uuid.uuid4().hex[:8]
            self.wrapper_root = os.path.join(self.source_root, wrapper_dirname)
            logger.info(f"Wrapper root not specified - using {self.wrapper_root}")

        if not os.path.isdir(self.wrapper_root):
            # Create the wrapper root directory if it doesn't exist
            logger.info(f"Creating wrapper root directory: {self.wrapper_root}")
            os.makedirs(self.wrapper_root)

        # Sanitize source_includes
        self.source_includes: list[str]  # type hinting
        if source_includes:
            self.source_includes = [
                os.path.abspath(include_path) for include_path in source_includes
            ]

            for include_path in self.source_includes:
                if not os.path.isdir(include_path):
                    logger.warning(
                        f"Could not find source include directory: {include_path}"
                    )
        else:
            self.source_includes = [self.source_root]

        # Sanitize package_info_path
        self.package_info_path: str | None = None
        if package_info_path:
            # If a package info config file is specified, check that it exists
            self.package_info_path = os.path.abspath(package_info_path)
            if not os.path.isfile(package_info_path):
                logger.error(f"Could not find package info file: {package_info_path}")
                raise FileNotFoundError()
        else:
            # If no package info config file has been supplied, check the default
            default_package_info_file = os.path.join(os.getcwd(), "package_info.yaml")
            if os.path.isfile(default_package_info_file):
                self.package_info_path = default_package_info_file
                logger.info(
                    f"Package info file not specified - using {default_package_info_file}"
                )
            else:
                logger.warning("No package info file found - using default settings.")

        # Initialize remaining attributes
        self.source_ns: pygccxml.declarations.namespace_t | None = None

        self.package_info: PackageInfo | None = None

        self.header_collection_filepath: str = os.path.join(
            self.wrapper_root, CPPWG_HEADER_COLLECTION_FILENAME
        )

    def log_unknown_classes(self) -> None:
        """
        Log unwrapped classes.
        """
        logger = logging.getLogger()

        all_class_decls = self.source_ns.classes(allow_empty=True)

        # Only report classes declared in the collected source headers, not ones
        # from their transitively-included dependencies (e.g. boost, PETSc, VTK).
        # A project may vendor such dependencies under the source root, so a
        # source-root path check would report - and log - thousands of
        # library-internal classes; matching against the source header set avoids
        # that noise and the associated slowdown.
        source_hpp_files = {
            os.path.realpath(f) for f in self.package_info.source_hpp_files
        }

        seen_class_names = set()
        for module_info in self.package_info.module_collection:
            for class_info in module_info.class_collection:
                seen_class_names.add(class_info.name)
                if class_info.decls:
                    seen_class_names.update(decl.name for decl in class_info.decls)

        for decl in all_class_decls:
            if decl.name in seen_class_names:
                continue

            if os.path.realpath(decl.location.file_name) not in source_hpp_files:
                continue

            seen_class_names.add(decl.name)  # e.g. Foo<2,2>
            seen_class_names.add(decl.name.split("<")[0].strip())  # e.g. Foo
            logger.info(
                f"Unknown class {decl.name} from {decl.location.file_name}:{decl.location.line}"
            )

        # Check for uninstantiated class templates not parsed by pygccxml
        for hpp_file_path in self.package_info.source_hpp_files:
            class_list = utils.find_classes_in_source_file(hpp_file_path)

            for _, class_name, _ in class_list:
                if class_name not in seen_class_names:
                    seen_class_names.add(class_name)
                    logger.info(f"Unknown class {class_name} from {hpp_file_path}")

    def parse_headers(self) -> None:
        """
        Parse the hpp files to collect C++ declarations.

        Parse the headers with pygccxml and castxml to populate the source
        namespace with C++ declarations collected from the source tree.
        """
        source_parser = CppSourceParser(
            self.source_root,
            self.header_collection_filepath,
            self.castxml_binary,
            self.source_includes,
            self.castxml_cflags,
            self.castxml_compiler,
            cache_path=self.cache_path,
        )
        self.source_ns = source_parser.parse()

    def discover_template_instantiations(self) -> None:
        """
        Discover explicit template instantiations from the source .cpp files.

        CastXML only parses the header collection, so templated classes that are
        only explicitly instantiated in implementation files
        (`template class Foo<2>;`) are invisible to the main parse. For classes
        that opt in via `discover_template_instantiations`, find those explicit
        instantiations and populate the classes' template args from them.

        The template arguments are read primarily from the instantiation source
        text, which is independent of how a given CastXML version renders
        defaulted template arguments (e.g. CastXML 0.4.4 names an instantiation
        of `AbstractMesh<2, 2>` as `AbstractMesh<2>`). CastXML/pygccxml is used
        only as a fallback for macro-generated instantiations, which the text
        scan cannot see: just the files whose instantiation marker yielded no
        literal `template class X<...>;` are parsed (parsing every candidate file
        would re-derive what the text scan already found, at a full CastXML run
        each). The fallback map is merged into the discovered args; merging a
        defaulted-argument class this way is only safe with CastXML >= 0.6.0
        (see PackageInfo.update_template_instantiations).
        """
        # Only do the work if some class actually needs discovery. Collecting
        # the implementation files walks the whole source tree, so it is
        # deferred until here rather than done for every generation run.
        if not self.package_info.uses_template_discovery():
            return

        self.package_info.collect_source_cpp(restricted_paths=[self.wrapper_root])

        # Read each implementation file once, collecting the files that contain
        # an explicit instantiation (directly or via a macro) and the
        # instantiation arguments found in their source text. Reading the
        # arguments from the text (the "primary" source) keeps them independent
        # of how a CastXML version renders defaulted template arguments.
        instantiation_map: dict[str, list[list[str]]] = {}
        macro_only_files: list[str] = []
        for filepath in self.package_info.source_cpp_files:
            has_instantiations, file_map = (
                utils.find_template_instantiations_in_source_file(filepath)
            )
            if not has_instantiations:
                continue

            if not file_map:
                # The file has an instantiation marker but the text scan found no
                # literal `template class X<...>;`, so its instantiations are
                # macro-generated and only the CastXML fallback can recover them.
                #
                # Note: a file that *mixes* literal and macro-generated
                # instantiations has a non-empty file_map, so it is not treated as
                # macro-only and its macro-generated instantiations are not
                # discovered. This is unsupported by auto-discovery; wrap those
                # instantiations by configuring template_substitutions for the
                # class manually.
                macro_only_files.append(filepath)
            for name, arg_lists in file_map.items():
                merged = instantiation_map.setdefault(name, [])
                for args in arg_lists:
                    if args not in merged:
                        merged.append(args)

        self.package_info.update_template_instantiations(instantiation_map)

        # Fallback: only macro-only files need CastXML. The text scan already
        # captured every literal `template class X<...>;`, so parsing the other
        # candidate files would just re-derive the same instantiations at the cost
        # of a full CastXML run each (hundreds, for a large project). A class that
        # is never instantiated in the source (e.g. an abstract base) simply is
        # not discovered - it has nothing to find. The fallback map is merged into
        # discovery-discovered args; template_substitutions still take precedence.
        if macro_only_files:
            source_parser = CppSourceParser(
                self.source_root,
                self.header_collection_filepath,
                self.castxml_binary,
                self.source_includes,
                self.castxml_cflags,
                self.castxml_compiler,
            )
            fallback_map = source_parser.parse_instantiations(macro_only_files)
            self.package_info.update_template_instantiations(
                fallback_map,
                merge=True,
                trust_defaulted_args=self.castxml_keeps_defaulted_args,
            )

    def parse_package_info(self) -> None:
        """
        Parse the package info file to create a PackageInfo object.
        """
        if self.package_info_path:
            # If a package info file exists, parse it to create a PackageInfo object
            info_parser = PackageInfoParser(self.package_info_path, self.source_root)
            self.package_info = info_parser.parse()

        else:
            # If no package info file exists, create a PackageInfo object with default settings
            self.package_info = PackageInfo("cppwg_package", self.source_root)

    def write_header_collection(self) -> None:
        """
        Write the header collection to file.
        """
        header_collection_writer = CppHeaderCollectionWriter(
            self.package_info,
            wrapper_templates.template_collection,
            self.wrapper_root,
            self.header_collection_filepath,
            self.overwrite,
        )
        header_collection_writer.write()

    def write_wrappers(self) -> None:
        """
        Write the wrapper code for the package.
        """
        package_writer = CppPackageWrapperWriter(
            self.package_info,
            wrapper_templates.template_collection,
            self.wrapper_root,
            self.overwrite,
        )
        package_writer.write()

    def generate(self) -> None:
        """
        Parse yaml configuration and C++ source to generate Python wrappers.
        """
        # Parse the input yaml for package, module, and class information
        self.parse_package_info()

        # Collect header files (skip wrappers), and update info
        self.package_info.init(restricted_paths=[self.wrapper_root])

        # Discover template instantiations from .cpp files (fallback for classes
        # that opt in and have no matching template_substitutions)
        self.discover_template_instantiations()

        # Write the header collection file
        self.write_header_collection()

        # Parse the headers with pygccxml (+ castxml)
        self.parse_headers()

        # Update info objects with data from the parsed source namespace
        self.package_info.update_from_ns(self.source_ns)

        # Discover instantiations of templated classes (e.g. abstract bases) that
        # are never explicitly instantiated but appear in the base-class
        # hierarchy of already-wrapped classes. These are already present in the
        # parsed namespace (implicitly instantiated via their concrete children)
        # and their wrappers are self-contained, so the header collection - only
        # the CastXML parse input - does not need re-writing for them.
        self.package_info.discover_base_class_instantiations(self.source_ns)

        # Drop wrapped instantiations that depend on an uninstantiated type
        # (which would otherwise fail to link/import), with a warning
        self.package_info.prune_uninstantiated_dependencies(
            restricted_paths=[self.wrapper_root]
        )

        # Log list of unknown classes in the source root
        self.log_unknown_classes()

        #  Write the wrapper code for the package
        self.write_wrappers()
