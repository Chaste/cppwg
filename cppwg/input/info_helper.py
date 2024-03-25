"""Helper utilities for info structures."""

import logging
import os
import re
from typing import Any, Dict, List

from cppwg.input.base_info import BaseInfo
from cppwg.input.class_info import CppClassInfo
from cppwg.input.module_info import ModuleInfo


class CppInfoHelper:
    """
    Adds information extracted from C++ source code to info objects.

    Helper class that attempts to automatically fill in extra feature
    information based on simple analysis of the source tree.

    __________
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
        self.class_dict: Dict[str, CppClassInfo] = {
            class_info.name: class_info
            for class_info in module_info.class_info_collection
        }

    def extract_templates_from_source(self, feature_info: BaseInfo) -> None:
        """
        Get template args from the source file associated with an info object.

        __________
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
        # e.g. {"signature":"<unsigned DIM_A,unsigned DIM_B>","replacement":[[2,2], [3,3]]}
        template_substitutions: List[Dict[str, Any]] = (
            feature_info.hierarchy_attribute_gather("template_substitutions")
        )

        # Skip if there are no template substitutions
        if len(template_substitutions) == 0:
            return

        # Remove spaces from template signatures
        # e.g. <unsigned DIM_A, unsigned DIM_B> -> <unsignedDIM_A,unsignedDIM_B>
        for tpl_sub in template_substitutions:
            tpl_sub["signature"] = tpl_sub["signature"].replace(" ", "")

        # Remove whitespaces, blank lines, and directives from the source file
        whitespace_regex = re.compile(r"\s+")
        with open(source_path, "r") as in_file:
            lines = [re.sub(whitespace_regex, "", line) for line in in_file]
            lines = [line for line in lines if line and not line.startswith("#")]

        # Search for template signatures in the source file lines
        for idx in range(len(lines) - 1):
            curr_line = lines[idx]
            next_line = lines[idx + 1]

            for template_substitution in template_substitutions:
                # e.g. template<unsignedDIM_A,unsignedDIM_B>
                signature: str = "template" + template_substitution["signature"]

                # e.g. [[2,2], [3,3]]
                replacement: List[List[Any]] = template_substitution["replacement"]

                if signature in curr_line:
                    feature_string = feature_type + feature_info.name  # e.g. "classFoo"

                    declaration_found = False

                    if feature_string == next_line:
                        # template<unsignedDIM_A,unsignedDIM_B>
                        # classFoo
                        declaration_found = True

                    elif next_line.startswith(feature_string + "{"):
                        # template<unsignedDIM_A,unsignedDIM_B>
                        # classFoo{
                        declaration_found = True

                    elif next_line.startswith(feature_string + ":"):
                        # template<unsignedDIM_A,unsignedDIM_B>
                        # classFoo:publicBar<DIM_A,DIM_B>
                        declaration_found = True

                    elif curr_line == signature + feature_string:
                        # template<unsignedDIM_A,unsignedDIM_B>classFoo
                        declaration_found = True

                    elif curr_line.startswith(signature + feature_string + "{"):
                        # template<unsignedDIM_A,unsignedDIM_B>classFoo{
                        declaration_found = True

                    elif curr_line.startswith(signature + feature_string + ":"):
                        # template<unsignedDIM_A,unsignedDIM_B>classFoo:publicBar<DIM_A,DIM_B>
                        declaration_found = True

                    if declaration_found:
                        feature_info.template_arg_lists = replacement
                        break
