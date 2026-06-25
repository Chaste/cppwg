"""Unit tests for cppwg.utils.utils."""

import os

from cppwg.utils.utils import write_file_if_changed


def test_writes_when_file_missing(tmp_path):
    """A new file is created and reports that it was written."""
    filepath = os.path.join(tmp_path, "wrapper.cpp")

    wrote = write_file_if_changed(filepath, "content")

    assert wrote is True
    assert os.path.isfile(filepath)
    with open(filepath) as f:
        assert f.read() == "content"


def test_skips_when_content_unchanged(tmp_path):
    """An identical file is left untouched, preserving its mtime."""
    filepath = os.path.join(tmp_path, "wrapper.cpp")
    with open(filepath, "w") as f:
        f.write("content")

    # Backdate the mtime so any rewrite would be detectable
    old_time = os.path.getmtime(filepath) - 100
    os.utime(filepath, (old_time, old_time))
    old_time_ns = os.stat(filepath).st_mtime_ns

    wrote = write_file_if_changed(filepath, "content")

    assert wrote is False
    assert os.stat(filepath).st_mtime_ns == old_time_ns


def test_rewrites_when_content_changed(tmp_path):
    """A file with different content is rewritten."""
    filepath = os.path.join(tmp_path, "wrapper.cpp")
    with open(filepath, "w") as f:
        f.write("old content")

    wrote = write_file_if_changed(filepath, "new content")

    assert wrote is True
    with open(filepath) as f:
        assert f.read() == "new content"


def test_overwrite_forces_rewrite_when_unchanged(tmp_path):
    """With overwrite=True, an identical file is rewritten anyway."""
    filepath = os.path.join(tmp_path, "wrapper.cpp")
    with open(filepath, "w") as f:
        f.write("content")

    old_time = os.path.getmtime(filepath) - 100
    os.utime(filepath, (old_time, old_time))
    old_time_ns = os.stat(filepath).st_mtime_ns

    wrote = write_file_if_changed(filepath, "content", overwrite=True)

    assert wrote is True
    assert os.stat(filepath).st_mtime_ns != old_time_ns
