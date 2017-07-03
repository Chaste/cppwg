"""
This file contains a list of classes that are to be wrapped.

Each class includes metadata such as template arguments, excluded methods,
methods with special pointer management requirements, and any special
declaration code needed for wrapping. A minimal case is just to
specify the class name and component it will belong to.
"""

import os


class CppClassInfoGenerator():

    """
    This attempts to automatically fill in some class info based on
    simple analysis of the source tree.
    """

    def __init__(self, source_root, wrapper_root, 
                 module_info):

        self.source_root = source_root
        self.wrapper_root = wrapper_root
        self.module_info = module_info

        # For covenience collect class info in a dict keyed by name
        self.class_dict = {}
        for eachClassInfo in self.module_info.class_info_collection:
            self.class_dict[eachClassInfo.name] = eachClassInfo

        # Template auto-replace
        self.template_substitutions = None

    def auto_expand_templates(self):

        if len(self.module_info.global_template_substitutions) == 0:
            return

        for eachClass in self.module_info.class_info_collection:
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

                for idx, eachSub in enumerate(self.module_info.global_template_substitutions):
                    template_args = eachSub['replacement']
                    template_string = eachSub['signature']
                    cleaned_string = template_string.replace(" ", "")
                    if cleaned_string in stripped_line:
                        class_string = "class" + eachClass.name
                        class_decl_next = class_string + ":" in stripped_next
                        class_decl_whole = class_string == stripped_next
                        if class_decl_next or class_decl_whole:
                            eachClass.template_args = template_args
                            break
            f.close()

    def do_custom_template_substitution(self):

        pass