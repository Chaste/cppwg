from typing import Any, Dict, List, Optional

from cppwg.input.base_info import BaseInfo


class PackageInfo(BaseInfo):
    """
    This class holds the package information

    Attributes
    ----------
    name : str
        The name of the package
    source_locations : List[str]
        A list of source locations for this package
    module_info_collection : List[ModuleInfo]
        A list of module info objects associated with this package
    source_root : str
        The root directory of the C++ source code
    source_hpp_patterns : List[str]
        A list of source file patterns to include
    source_hpp_files : List[str]
        A list of source file names to include
    common_include_file : bool
        Use a common include file for all source files
    """

    def __init__(
        self,
        name: str,
        source_root: str,
        package_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Parameters:
        -----------
        name : str
        source_root : str
        package_config : Dict[str, Any]
            A dictionary of package configuration settings
        """

        super(PackageInfo, self).__init__(name)

        self.name: str = name
        self.source_locations: List[str] = None
        self.module_info_collection: List["ModuleInfo"] = []  # noqa: F821
        self.source_root: str = source_root
        self.source_hpp_patterns: List[str] = ["*.hpp"]
        self.source_hpp_files: List[str] = []
        self.common_include_file: bool = False

        if package_config:
            for key, value in package_config.items():
                setattr(self, key, value)

    @property
    def parent(self) -> None:
        """
        Returns None as this is the top level object in the hierarchy
        """
        return None
