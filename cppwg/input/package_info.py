from typing import Any, Optional

from cppwg.input.base_info import BaseInfo


class PackageInfo(BaseInfo):
    """
    This class holds the package information
    """

    def __init__(
        self,
        name: str,
        source_root: str,
        package_config: Optional[dict[str, Any]] = None,
    ):
        """
        Parameters:
        -----------
            name : str
                The name of the package
            source_root : str
                The root directory of the C++ source code
            package_config : dict[str, Any]
                A dictionary of package configuration settings
        """

        super(PackageInfo, self).__init__(name)

        self.name = name
        self.source_locations = None
        self.module_info_collection = []
        self.source_root = source_root
        self.source_hpp_patterns = ["*.hpp"]
        self.source_hpp_files = []
        self.common_include_file = False

        if package_config:
            for key, value in package_config.items():
                setattr(self, key, value)

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
