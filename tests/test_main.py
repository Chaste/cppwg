"""Unit tests for cppwg.__main__."""

import re

from cppwg.__main__ import timestamped_logfile


def test_timestamped_logfile_inserts_timestamp():
    """A timestamp is inserted before the suffix, keeping the directory/stem."""
    result = timestamped_logfile("/var/log/cppwg.log")
    assert re.fullmatch(r"/var/log/cppwg_\d{8}-\d{6}\.log", result)


def test_timestamped_logfile_bare_name():
    """A bare filename (no directory) is handled."""
    result = timestamped_logfile("cppwg.log")
    assert re.fullmatch(r"cppwg_\d{8}-\d{6}\.log", result)


def test_timestamped_logfile_unique_per_call(monkeypatch):
    """Successive runs (different times) produce different filenames."""
    from cppwg import __main__ as main_module

    times = iter(["20260708-153012", "20260708-153030"])

    class _FixedDatetime:
        @staticmethod
        def now():
            class _Now:
                @staticmethod
                def strftime(fmt):
                    return next(times)

            return _Now()

    monkeypatch.setattr(main_module, "datetime", _FixedDatetime)
    first = timestamped_logfile("cppwg.log")
    second = timestamped_logfile("cppwg.log")
    assert first == "cppwg_20260708-153012.log"
    assert second == "cppwg_20260708-153030.log"
    assert first != second
