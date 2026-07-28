"""Unit tests for cppwg.__main__."""

import argparse
import logging
import os
import re
import sys
from datetime import datetime

import pytest

from cppwg import __main__ as main_module
from cppwg.__main__ import generate, main, parse_args, rotate_logfile


@pytest.fixture
def isolated_logging():
    """Snapshot and restore the root logger so main()'s handlers don't leak."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    root.handlers = []
    yield
    for handler in root.handlers:
        handler.close()
    root.handlers = saved_handlers
    root.setLevel(saved_level)


def _args(**overrides):
    """Build a parsed-args namespace with generate()'s expected attributes."""
    defaults = dict(
        source_root="/src",
        includes=None,
        wrapper_root=None,
        package_info=None,
        castxml_binary=None,
        castxml_compiler=None,
        std=None,
        castxml_cflags=None,
        overwrite=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


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


def test_parse_args_reads_all_options(monkeypatch):
    """Command-line options are parsed onto the namespace."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cppwg", "/src",
            "-w", "/out",
            "-p", "cfg.yaml",
            "-c", "/bin/castxml",
            "-m", "/bin/gcc",
            "--std", "c++17",
            "--castxml_cflags=-Wno-deprecated",
            "-i", "inc_a", "inc_b",
            "--overwrite",
            "-q",
            "-l", "run.log",
        ],
    )
    args = parse_args()
    assert args.source_root == "/src"
    assert args.wrapper_root == "/out"
    assert args.package_info == "cfg.yaml"
    assert args.castxml_binary == "/bin/castxml"
    assert args.castxml_compiler == "/bin/gcc"
    assert args.std == "c++17"
    assert args.castxml_cflags == "-Wno-deprecated"
    assert args.includes == ["inc_a", "inc_b"]
    assert args.overwrite is True
    assert args.quiet is True
    assert args.logfile == "run.log"


def test_parse_args_logfile_const_and_default(monkeypatch):
    """-l with no value uses the const filename; omitting it leaves None."""
    monkeypatch.setattr(sys, "argv", ["cppwg", "/src", "-l"])
    assert parse_args().logfile == "cppwg.log"

    monkeypatch.setattr(sys, "argv", ["cppwg", "/src"])
    assert parse_args().logfile is None


def test_generate_builds_generator_and_runs(monkeypatch):
    """generate() constructs the generator with combined cflags and runs it."""
    captured = {}

    class _FakeGenerator:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def generate(self):
            captured["generated"] = True

    monkeypatch.setattr(main_module, "CppWrapperGenerator", _FakeGenerator)

    generate(_args(std="c++17", castxml_cflags="-w", includes=["inc"]))

    assert captured["source_root"] == "/src"
    assert captured["source_includes"] == ["inc"]
    assert captured["castxml_cflags"] == "-std=c++17 -w"
    assert captured["generated"] is True


def test_generate_without_std_or_cflags_passes_none(monkeypatch):
    """With neither --std nor --castxml_cflags, cflags is None."""
    captured = {}

    class _FakeGenerator:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def generate(self):
            pass

    monkeypatch.setattr(main_module, "CppWrapperGenerator", _FakeGenerator)

    generate(_args())

    assert captured["castxml_cflags"] is None


def test_generate_rejects_multi_token_std(monkeypatch):
    """A --std value smuggling extra flags is rejected before generation."""
    monkeypatch.setattr(main_module, "CppWrapperGenerator", object)

    with pytest.raises(SystemExit):
        generate(_args(std="c++17 -w"))


def test_main_sets_up_logfile_and_runs_generate(monkeypatch, tmp_path, isolated_logging):
    """main() configures a log file and delegates to generate()."""
    seen = {}
    monkeypatch.setattr(main_module, "generate", lambda args: seen.setdefault("args", args))

    logfile = tmp_path / "cppwg.log"
    monkeypatch.setattr(sys, "argv", ["cppwg", "/src", "-l", str(logfile)])

    main()

    assert seen["args"].source_root == "/src"
    assert logfile.is_file()


def test_main_quiet_without_logfile(monkeypatch, isolated_logging):
    """main() runs with --quiet and no log file without error."""
    seen = {}
    monkeypatch.setattr(main_module, "generate", lambda args: seen.setdefault("ran", True))
    monkeypatch.setattr(sys, "argv", ["cppwg", "/src", "-q"])

    main()

    assert seen["ran"] is True
