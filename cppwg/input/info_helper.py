import os
import re
import logging

from cppwg.input.base_info import BaseInfo
from cppwg.input.class_info import CppClassInfo
from cppwg.input.module_info import ModuleInfo


class CppInfoHelper:
    """
    Helper class that attempts to automatically fill in extra feature
    information based on simple analysis of the source tree.

    Attributes
    __________
    module_info : ModuleInfo
        The module info object that this helper is working with.
    class_dict : dict
        A dictionary of class info objects keyed by class name.
    """

    def __init__(self, module_info: ModuleInfo):

        self.module_info: ModuleInfo = module_info

        # For convenience, collect class info in a dict keyed by name
        self.class_dict: dict[str, CppClassInfo] = {
            class_info.name: class_info
            for class_info in module_info.class_info_collection
        }

    def extract_templates_from_source(self, feature_info: BaseInfo) -> None:
        """
        Extract template arguments for a feature from the associated source
        file.

        Parameters
        __________
        feature_info : BaseInfo
            The feature info object to expand.
        """
        logger = logging.getLogger()

        if isinstance(feature_info, CppClassInfo):
            feature_type = "class"
        else:
            logger.error(f"Unsupported feature type: {type(feature_info)}")
            raise TypeError()

        # Skip if there are pre-defined template args
        if feature_info.template_arg_lists:
            return

        # Skip if there is no source file
        source_path = feature_info.source_file_full_path
        if not source_path:
            return

        if not os.path.isfile(source_path):
            logger.error(f"Could not find source file: {source_path}")
            raise FileNotFoundError()

        # Get list of template substitutions from this feature and its parents
        # e.g. {"signature":"<unsigned DIM,unsigned DIM>","replacement":[[2,2], [3,3]]}
        template_substitutions: list[dict[str, str]] = (
            feature_info.hierarchy_attribute_gather("template_substitutions")
        )

        # Skip if there are no template substitutions
        if len(template_substitutions) == 0:
            return

        # Remove spaces from template substitution signatures
        # e.g. <unsigned DIM, unsigned DIM> -> <unsignedDIM,unsignedDIM>
        for tpl_sub in template_substitutions:
            tpl_sub["signature"] = tpl_sub["signature"].replace(" ", "")

        # Remove whitespace and blank lines from the source file
        whitespace_regex = re.compile(r"\s+")
        with open(source_path, "r") as in_file:
            lines = [re.sub(whitespace_regex, "", line) for line in in_file]
            lines = [line for line in lines if line]

        # Search for template signatures in the source file lines
        for idx in range(len(lines) - 1):
            curr_line = lines[idx]
            next_line = lines[idx + 1]

            for template_substitution in template_substitutions:
                # e.g. <unsignedDIM,unsignedDIM>
                signature = template_substitution["signature"]

                # e.g. [[2,2], [3,3]]
                replacement = template_substitution["replacement"]

                if signature in curr_line:
                    feature_string = feature_type + feature_info.name  # e.g. "classFoo"

                    # Simple declaration example:
                    # template<unsignedDIM,unsignedDIM>
                    # classFoo
                    simple_declaration = feature_string == next_line

                    # Derived declaration example:
                    # template<unsignedDIM>
                    # classFoo:publicBar<DIM,DIM>
                    derived_declaration = feature_string + ":" in next_line

                    # TODO: Add support for more cases
                    # e.g.
                    # template<unsignedDIM,unsignedDIM> classFoo
                    # template<unsignedDIM> classFoo:publicBar<DIM,DIM>

                    if simple_declaration or derived_declaration:
                        feature_info.template_arg_lists = replacement
                        break
