import os

from typing import Any, Optional

from cppwg.input.base_info import BaseInfo

from pygccxml.declarations import declaration_t


class ModuleInfo(BaseInfo):
    """
    This class holds information for individual modules

    Attributes
    ----------
    package_info : PackageInfo
        The package info parent object associated with this module
    source_locations : list[str]
        A list of source locations for this module
    class_info_collection : list[CppClassInfo]
        A list of class info objects associated with this module
    free_function_info_collection : list[CppFreeFunctionInfo]
        A list of free function info objects associated with this module
    variable_info_collection : list[CppFreeFunctionInfo]
        A list of variable info objects associated with this module
    use_all_classes : bool
        Use all classes in the module
    use_all_free_functions : bool
        Use all free functions in the module
    use_all_variables : bool
        Use all variables in the module
    """

    def __init__(self, name: str, module_config: Optional[dict[str, Any]] = None):

        super(ModuleInfo, self).__init__(name)

        self.package_info: Optional["PackageInfo"] = None
        self.source_locations: list[str] = None
        self.class_info_collection: list["CppClassInfo"] = []
        self.free_function_info_collection: list["CppFreeFunctionInfo"] = []
        self.variable_info_collection: list["CppFreeFunctionInfo"] = []
        self.use_all_classes: bool = False
        self.use_all_free_functions: bool = False
        self.use_all_variables: bool = False

        if module_config:
            for key, value in module_config.items():
                setattr(self, key, value)

    @property
    def parent(self) -> "PackageInfo":
        """
        Returns the parent package info object
        """
        return self.package_info

    def is_decl_in_source_path(self, decl: declaration_t) -> bool:
        """
        Check if the declaration is associated with a file in the current source path

        Parameters
        ----------
        decl : declaration_t
            The declaration to check

        Returns
        -------
        bool
            True if the declaration is associated with a file in the current source path
        """

        if self.source_locations is None:
            return True

        for source_location in self.source_locations:
            full_path = os.path.join(self.package_info.source_root, source_location)
            if full_path in decl.location.file_name:
                return True
        return False
