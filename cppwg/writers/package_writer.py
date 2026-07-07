"""Wrapper code writer for the package."""

from typing import TYPE_CHECKING

from cppwg.writers.module_writer import CppModuleWrapperWriter

if TYPE_CHECKING:
    from string import Template

    from cppwg.info.package_info import PackageInfo


class CppPackageWrapperWriter:
    """
    Class to generates Python bindings for all modules in the package.

    Attributes
    ----------
    package_info : PackageInfo
        The package information to generate Python bindings for
    wrapper_templates : dict[str, Template]
        Templates with placeholders for generating wrapper code
    wrapper_root : str
        The output directory for the generated wrapper code
    overwrite : bool
        Force rewrite of all wrapper files, even if unchanged
    """

    def __init__(
        self,
        package_info: "PackageInfo",
        wrapper_templates: dict[str, "Template"],
        wrapper_root: str,
        overwrite: bool = False,
    ):
        self.package_info = package_info
        self.wrapper_templates = wrapper_templates
        self.wrapper_root = wrapper_root
        self.overwrite = overwrite

    def write(self) -> None:
        """
        Write all the wrappers required for the package.
        """
        for module_info in self.package_info.module_collection:
            module_writer = CppModuleWrapperWriter(
                module_info,
                self.wrapper_templates,
                self.wrapper_root,
                self.overwrite,
            )
            module_writer.write()
