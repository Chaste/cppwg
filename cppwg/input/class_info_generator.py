"""
This file contains a list of classes that are to be wrapped.

Each class includes metadata such as template arguments, excluded methods,
methods with special pointer management requirements, and any special
declaration code needed for wrapping. A minimal case is just to
specify the class name and component it will belong to.
"""

import os
import fnmatch


class CppClassInfoGenerator():

    """
    This attempts to automatically fill in some class info based on
    simple analysis of the source tree.
    """

    def __init__(self, source_root, wrapper_root, class_info_collection):

        self.source_root = source_root
        self.wrapper_root = wrapper_root
        self.class_info_collection = class_info_collection

        # For covenience collect class info in a dict keyed by name
        self.class_dict = {}
        for eachClass in self.class_info_collection:
            self.class_dict[eachClass.name] = eachClass

        # Try to identify modules automatically
        self.module_keys = None
        self.attempt_auto_module_id = True

        # Template auto-replace
        self.template_substitutions = None

    def assign_include_paths(self):

        for root, _, filenames in os.walk(self.source_root, followlinks=True):
            for filename in fnmatch.filter(filenames, '*.hpp'):
                filename_no_ext = os.path.splitext(filename)[0]
                if filename_no_ext in self.class_dict.keys():
                    full_path = os.path.join(root, filename)
                    self.class_dict[filename_no_ext].full_path = full_path

    def assign_module_by_directory(self):

        # Set the component name
        for eachClass in self.class_info_collection:
            if eachClass.component is None and eachClass.full_path is not None:
                for eachKey in self.module_keys.keys():
                    if "/" + eachKey + "/" in eachClass.full_path:
                        eachClass.component = self.module_keys[eachKey]

    def auto_expand_templates(self):

        for eachClass in self.class_info_collection:

            # Skip any classes with pre-defined template args
            no_template = eachClass.template_args is None
            has_path = eachClass.full_path is not None
            if not (no_template and has_path):
                continue

            if not os.path.exists(eachClass.full_path):
                continue

            f = open(eachClass.full_path)
            lines = (line.rstrip() for line in f)  # Remove blank lines

            lines = list(line for line in lines if line)
            for idx, eachLine in enumerate(lines):
                stripped_line = eachLine.replace(" ", "")
                if idx+1 < len(lines):
                    stripped_next = lines[idx+1].replace(" ", "")
                else:
                    continue

                for eachTemplateString in self.template_substitutions.keys():
                    cleaned_string = eachTemplateString.replace(" ", "")
                    if cleaned_string in stripped_line:
                        class_string = "class" + eachClass.name
                        class_decl_next = class_string + ":" in stripped_next
                        class_decl_whole = class_string == stripped_next
                        if class_decl_next or class_decl_whole:
                            template_args = self.template_substitutions[eachTemplateString]
                            eachClass.template_args = template_args
                            break
            f.close()

    def do_custom_template_substitution(self):

        pass

    def generate_class_info(self):

        self.assign_include_paths()

        if self.attempt_auto_module_id:
            self.assign_module_by_directory()

        self.auto_expand_templates()
        self.do_custom_template_substitution()

        with open(self.wrapper_root + "/class_data.p", 'wb') as fp:
            pickle.dump(self.class_info_collection, fp)