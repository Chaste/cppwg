from cppwg.input import base_info

class ModuleInfo(base_info.BaseInfo):
    """
    Information for individual modules
    """

    def __init__(self, name, type_info_dict = None):
        
        super(ModuleInfo, self).__init__(name)

        self.package_info = None
        self.source_locations = None
        self.class_info_collection = []
        self.free_function_info_collection = []
        self.variable_info_collection = []
        self.use_all_classes = False
        self.use_all_free_functions = False
        
        if type_info_dict is not None:
            for key in type_info_dict:
                setattr(self, key, type_info_dict[key])  
                
    @property
    def parent(self):
        return self.package_info

    def is_decl_in_source_path(self, decl):

        """
        Return is the declaration associated with a file in the current source path
        """

        if self.source_locations is None:
            return True

        for eachSourceLocation in self.source_locations:
            location = self.package_info.source_root + "/" + eachSourceLocation + "/"
            if location in decl.location.file_name:
                return True
        return False
