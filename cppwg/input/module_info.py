"""
Information for individual modules
"""


class CppModuleInfo():

    """
    Information for individual modules
    """

    def __init__(self, name, source_root,
                 source_locations=None,
                 class_info_collection=None,
                 free_function_info_collection=None,
                 use_all_classes=False,
                 use_all_functions=False,
                 common_include_file=True,
                 global_includes=None,
                 smart_ptr_type=None,
                 global_calldef_excludes=None,
                 global_template_substitutions=None):

        self.name = name
        self.source_locations = source_locations
        self.class_info_collection = class_info_collection
        self.source_root = source_root
        self.free_function_info_collection = free_function_info_collection
        self.use_all_classes = use_all_classes
        self.use_all_free_functions = use_all_functions
        self.common_include_file = common_include_file
        self.smart_ptr_type = smart_ptr_type
        self.global_calldef_excludes = global_calldef_excludes
        if self.global_calldef_excludes is None:
            self.global_calldef_excludes = global_calldef_excludes
        if global_includes is None:
            self.global_includes = []
        else:
            self.global_includes = global_includes
        if global_template_substitutions is None:
            self.global_template_substitutions = []
        else:
            self.global_template_substitutions = global_template_substitutions

    def decl_in_source_path(self, decl):

        """
        Return is the declaration associated with a file in the current source tree
        """

        if self.source_locations is None:
            return True

        for eachSourceLocation in self.source_locations:
            location = self.source_root + "/" + eachSourceLocation + "/"
            if location in decl.location.file_name:
                return True
        return False
