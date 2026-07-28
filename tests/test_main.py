"""Unit tests for cppwg.__main__."""

import os
import re
from datetime import datetime

from cppwg.__main__ import rotate_logfile


def test_rotate_logfile_absent_is_noop(tmp_path):
    """A missing log file needs no rotation and leaves the directory empty."""
    logfile = tmp_path / "cppwg.log"
    rotate_logfile(str(logfile))
    assert not logfile.exists()
    assert list(tmp_path.iterdir()) == []


def test_rotate_logfile_renames_existing_by_mtime(tmp_path):
    """An existing log is renamed with its own mtime inserted before the suffix."""
    logfile = tmp_path / "cppwg.log"
    logfile.write_text("previous run")

    # Pin the modification time so the rotated name is deterministic.
    mtime = datetime(2026, 7, 8, 15, 30, 12).timestamp()
    os.utime(logfile, (mtime, mtime))

    rotate_logfile(str(logfile))

    assert not logfile.exists()
    rotated = tmp_path / "cppwg_20260708-153012.log"
    assert rotated.exists()
    assert rotated.read_text() == "previous run"


def test_rotate_logfile_keeps_stem_and_suffix(tmp_path):
    """Rotation preserves the stem and suffix around the inserted timestamp."""
    logfile = tmp_path / "cppwg.log"
    logfile.write_text("x")

    rotate_logfile(str(logfile))

    assert not logfile.exists()
    contents = list(tmp_path.iterdir())
    assert len(contents) == 1
    assert re.fullmatch(r"cppwg_\d{8}-\d{6}\.log", contents[0].name)


def test_rotate_logfile_does_not_overwrite_same_timestamp(tmp_path):
    """A rotated name that already exists is disambiguated, never overwritten."""
    logfile = tmp_path / "cppwg.log"
    logfile.write_text("newer run")
    mtime = datetime(2026, 7, 8, 15, 30, 12).timestamp()
    os.utime(logfile, (mtime, mtime))

    # A previous run already rotated to this exact mtime-second name.
    existing = tmp_path / "cppwg_20260708-153012.log"
    existing.write_text("older run")

    rotate_logfile(str(logfile))

    assert not logfile.exists()
    assert existing.read_text() == "older run"  # untouched
    disambiguated = tmp_path / "cppwg_20260708-153012-1.log"
    assert disambiguated.read_text() == "newer run"


def test_rotate_logfile_ignores_directory(tmp_path):
    """A directory at the log path is left untouched, not renamed."""
    logdir = tmp_path / "cppwg.log"
    logdir.mkdir()

    rotate_logfile(str(logdir))

    assert logdir.is_dir()
    assert [p.name for p in tmp_path.iterdir()] == ["cppwg.log"]
