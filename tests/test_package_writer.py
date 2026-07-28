"""Unit tests for cppwg.writers.package_writer."""

from cppwg.writers import package_writer
from cppwg.writers.package_writer import CppPackageWrapperWriter


def test_write_delegates_to_a_module_writer_per_module(monkeypatch):
    """Each module in the package is written by its own module writer."""
    written = []

    class _FakeModuleWriter:
        def __init__(self, module_info, templates, root, overwrite):
            self.module_info = module_info
            self.overwrite = overwrite

        def write(self):
            written.append((self.module_info, self.overwrite))

    monkeypatch.setattr(package_writer, "CppModuleWrapperWriter", _FakeModuleWriter)

    class _FakePackage:
        module_collection = ["mod_a", "mod_b"]

    writer = CppPackageWrapperWriter(
        _FakePackage(), {"tpl": "x"}, "/out", overwrite=True
    )
    writer.write()

    assert written == [("mod_a", True), ("mod_b", True)]
