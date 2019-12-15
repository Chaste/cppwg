"""
Helper class for generating extra feature information based
on simple analysis of the source tree.
"""

import os


class CppInfoHelper(object):

    """
    This attempts to automatically fill in some class info based on
    simple analysis of the source tree.
    """

    def __init__(self, module_info):

        self.module_info = module_info
        
        self.class_dict = {}
        self.setup_class_dict()
        
    def setup_class_dict(self):

        # For convenience collect class info in a dict keyed by name
        for eachClassInfo in self.module_info.class_info:
            self.class_dict[eachClassInfo.name] = eachClassInfo

    def expand_templates(self, feature_info, feature_type):

        template_substitutions = feature_info.hierarchy_attribute_gather('template_substitutions')
        
        if len(template_substitutions) == 0:
            return

        # Skip any features with pre-defined template args
        no_template = feature_info.template_args is None
        source_path = feature_info.source_file_full_path
        if not (no_template and source_path is not None):
            return
        if not os.path.exists(source_path):
            return

        f = open(source_path)
        lines = (line.rstrip() for line in f)  # Remove blank lines

        lines = list(line for line in lines if line)
        for idx, eachLine in enumerate(lines):
            stripped_line = eachLine.replace(" ", "")
            if idx+1 < len(lines):
                stripped_next = lines[idx+1].replace(" ", "")
            else:
                continue

            for idx, eachSub in enumerate(template_substitutions):
                template_args = eachSub['replacement']
                template_string = eachSub['signature']
                cleaned_string = template_string.replace(" ", "")
                if cleaned_string in stripped_line:
                    feature_string = feature_type + feature_info.name
                    feature_decl_next = feature_string + ":" in stripped_next
                    feature_decl_whole = feature_string == stripped_next
                    if feature_decl_next or feature_decl_whole:
                        feature_info.template_args = template_args
                        break
        f.close()

    def do_custom_template_substitution(self, feature_info):

        pass