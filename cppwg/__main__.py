"""Entry point for the cppwg package."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from cppwg import CppWrapperGenerator
from cppwg.utils.constants import CPPWG_DEFAULT_LOGFILE
from cppwg.version import __version__


def rotate_logfile(logfile: str) -> None:
    """
    Rotate an existing log file out of the way so the next run can reuse its name.

    If a log file already exists at the path, it is renamed with its own
    last-modification time inserted before the suffix, e.g.
    "cppwg.log" -> "cppwg_20260708-153012.log". The new run then writes to the
    original name, so the requested path always holds the latest run while
    earlier runs are preserved under timestamped names. A trailing "-N" is added
    if a log with that timestamp already exists, so a previous run is never
    overwritten (and the rename does not raise on Windows, where it would not
    replace an existing destination). Non-file paths (e.g. a directory) are left
    untouched.

    Parameters
    ----------
    logfile : str
        The requested log file path.
    """
    path = Path(logfile)
    if not path.is_file():
        return

    timestamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d-%H%M%S")
    rotated = path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
    counter = 1
    while rotated.exists():
        rotated = path.with_name(f"{path.stem}_{timestamp}-{counter}{path.suffix}")
        counter += 1

    path.rename(rotated)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns
    -------
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="cppwg",
        description="Generate Python Wrappers for C++ code",
        epilog="Run 'cppwg genpackage --help' for the Python package-layer generator.",
    )

    parser.add_argument(
        "source_root",
        metavar="SOURCE_ROOT",
        type=str,
        help="Path to the root directory of the input C++ source code.",
    )

    parser.add_argument(
        "-w",
        "--wrapper_root",
        type=str,
        help="Path to the output directory for the Pybind11 wrapper code.",
    )

    parser.add_argument(
        "-p", "--package_info", type=str, help="Path to the package info file."
    )

    parser.add_argument(
        "-c",
        "--castxml_binary",
        type=str,
        help="Path to the castxml executable.",
    )

    parser.add_argument(
        "-m",
        "--castxml_compiler",
        type=str,
        help="Path to a compiler to be used by castxml.",
    )

    # Note: --std is offered as a convenience so the common case does not need
    # the awkward --castxml_cflags="-std=c++17" syntax. A value starting with
    # "-" must be passed with "=" (e.g. --castxml_cflags="-w"), otherwise
    # argparse treats it as a new argument. See https://bugs.python.org/issue9334
    parser.add_argument(
        "--std",
        type=str,
        help="C++ standard e.g. c++17.",
    )

    parser.add_argument(
        "--castxml_cflags",
        type=str,
        help="Additional flags for the castxml clang frontend. Pass values "
        'starting with "-" using "=" e.g. --castxml_cflags="-Wno-deprecated".',
    )

    parser.add_argument(
        "-i",
        "--includes",
        type=str,
        nargs="*",
        help="List of paths to include directories.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Force rewrite of all wrapper files, even if unchanged. By default, "
        "unchanged wrapper files are left untouched to speed up rebuilds.",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Disable informational messages.",
    )

    parser.add_argument(
        "-l",
        "--logfile",
        type=str,
        nargs="?",
        default=None,
        const=CPPWG_DEFAULT_LOGFILE,
        help="Output log messages to a file.",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
        help="Print cppwg version.",
    )

    args = parser.parse_args()

    return args


def generate(args: argparse.Namespace) -> None:
    """
    Generate the Python wrappers.

    Parameters
    ----------
    args : argparse.Namespace
        The parsed command line arguments.
    """
    logger = logging.getLogger()

    castxml_cflags = ""
    std = args.std.strip() if args.std else ""
    if std:
        # Only the first token is the C++ standard. Reject any extra tokens to
        # prevent smuggling additional flags in through --std (e.g.
        # --std "c++17 -w"); these should be passed via --castxml_cflags.
        std, *extra = std.split()
        if extra:
            logger.error(
                f"Invalid --std value {args.std!r}: expected a single token like 'c++17'. "
                "Pass additional flags via --castxml_cflags."
            )
            raise SystemExit(1)
        castxml_cflags = f"-std={std}"
    if args.castxml_cflags:
        castxml_cflags = f"{castxml_cflags} {args.castxml_cflags}".strip()

    generator = CppWrapperGenerator(
        source_root=args.source_root,
        source_includes=args.includes,
        wrapper_root=args.wrapper_root,
        package_info_path=args.package_info,
        castxml_binary=args.castxml_binary,
        castxml_cflags=castxml_cflags or None,
        castxml_compiler=args.castxml_compiler,
        overwrite=args.overwrite,
    )

    generator.generate()


def main() -> None:
    """Generate wrappers from command line arguments.

    ``cppwg genpackage ...`` is dispatched to the package-layer generator
    (:mod:`cppwg.genpackage`); any other invocation runs wrapper generation as
    usual. The subcommand is intercepted before argument parsing so the normal
    CLI (a leading ``SOURCE_ROOT`` positional) is entirely unaffected.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "genpackage":
        from cppwg.genpackage import main as genpackage_main

        raise SystemExit(genpackage_main(sys.argv[2:]))

    args = parse_args()

    log_handlers = []

    # Set up logging
    stream_handler = logging.StreamHandler()
    if args.quiet:
        stream_handler.setLevel(logging.ERROR)
    else:
        stream_handler.setLevel(logging.INFO)
    log_handlers.append(stream_handler)

    logfile = None
    if args.logfile:
        # Write to the requested path, rotating any existing log out of the way
        # first so previous runs are preserved under timestamped names.
        logfile = args.logfile
        rotate_logfile(logfile)
        file_handler = logging.FileHandler(logfile, "w")
        file_handler.setLevel(logging.INFO)
        log_handlers.append(file_handler)

    logging.basicConfig(
        format="%(levelname)s %(message)s",
        handlers=log_handlers,
    )
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logfile:
        logger.info(f"Logging to {logfile}")

    # Generate the wrappers
    generate(args)


if __name__ == "__main__":
    main()
