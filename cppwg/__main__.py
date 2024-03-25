"""Entry point for the cppwg package."""

import argparse
import logging

from cppwg import CppWrapperGenerator, __version__


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

    # Note: we're passing in std directly because syntax like
    # --castxml_cflags "-std=c++17" isn't supported by argparse because of
    # the initial "-" in the argument. See https://bugs.python.org/issue9334
    parser.add_argument(
        "--std",
        type=str,
        help="C++ standard e.g. c++17.",
    )

    parser.add_argument(
        "-i",
        "--includes",
        type=str,
        nargs="*",
        help="List of paths to include directories.",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Disable informational messages.",
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
    castxml_cflags = None
    if args.std:
        castxml_cflags = f"-std={args.std}"

    generator = CppWrapperGenerator(
        source_root=args.source_root,
        source_includes=args.includes,
        wrapper_root=args.wrapper_root,
        package_info_path=args.package_info,
        castxml_binary=args.castxml_binary,
        castxml_cflags=castxml_cflags,
    )

    generator.generate_wrapper()


def main() -> None:
    """Generate wrappers from command line arguments."""
    args = parse_args()

    logging.basicConfig(
        format="%(levelname)s %(message)s",
        handlers=[logging.FileHandler("cppwg.log"), logging.StreamHandler()],
    )
    logger = logging.getLogger()

    if args.quiet:
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)

    generate(args)


if __name__ == "__main__":
    main()
