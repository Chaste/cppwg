"""
Information for the package
"""

import base_info


class PackageInfo(base_info.BaseInfo):

    """
    Information for individual modules
    """

    def __init__(self, name, source_root,  type_info_dict = None):
        
        super(PackageInfo, self).__init__(name)

        self.name = name
        self.source_locations = None
        self.module_info = []
        self.source_root = source_root
        self.source_hpp_patterns = ["*.hpp"]
        self.source_hpp_files = []
        self.common_include_file = False
        
        if type_info_dict is not None:
            for key in type_info_dict:
                setattr(self, key, type_info_dict[key])  
                
    @property
    def parent(self):
        return None
        
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
