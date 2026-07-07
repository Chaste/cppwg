"""Unit tests for cppwg.info.package_info."""

import os

from cppwg.info.package_info import PackageInfo


def test_collect_source_headers_skips_restricted_paths(tmp_path):
    """Headers under a restricted path are excluded from the source collection.

    Regression test: the restricted-path skip previously used a `continue`
    inside the restricted_paths loop, which only advanced that loop instead of
    skipping the file, so a header under a restricted path (e.g. the wrapper
    output directory nested in the source root) was collected anyway.
    """
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    wrapper = src / "wrapper"
    wrapper.mkdir()

    (src / "Keep.hpp").write_text("")
    # A plain header inside the restricted path. It is not a .cppwg.hpp file, so
    # only the restricted-path check can exclude it.
    (wrapper / "Skip.hpp").write_text("")

    package_info = PackageInfo("testpkg", {"source_root": str(src)})
    package_info.collect_source_headers(restricted_paths=[str(wrapper)])

    basenames = {os.path.basename(f) for f in package_info.source_hpp_files}
    assert "Keep.hpp" in basenames
    assert "Skip.hpp" not in basenames
