import os
import subprocess
import unittest
from glob import glob
from typing import List


def get_file_lines(file_path: str) -> List[str]:
    """
    Load a file into a list of lines

    Parameters
    ----------
    file_path : str
      The path to the file to load

    Returns
    -------
    List[str]
      A list of lines read from the file, with excess whitespace and empty lines removed
    """

    with open(file_path, "r") as in_file:
        # remove excess whitespace
        lines = [line.rstrip().lstrip() for line in in_file]
        # remove empty lines
        lines = [line for line in lines if line]

    return lines


def compare_files(file_path_a: str, file_path_b: str) -> bool:
    """
    Check if two files have the same content

    Parameters
    __________
    file_path_a: str
        The path to the first file
    file_path_b: str
        The path to the second file

    Returns
    __________
    bool
        True if the files have the same content
    """
    # Get file lines with whitespace and empty lines stripped
    file_lines_a = get_file_lines(file_path_a)
    file_lines_b = get_file_lines(file_path_b)

    return file_lines_a == file_lines_b


class TestShapes(unittest.TestCase):

    def test_wrapper_generation(self) -> None:
        """
        Generate wrappers and compare with the reference wrappers.
        """

        # Set paths to the shapes code, reference and generated wrappers, etc.
        shapes_root = os.path.abspath("examples/shapes")
        shapes_src = os.path.join(shapes_root, "src")

        wrapper_root_ref = os.path.join(shapes_root, "wrapper")
        wrapper_root_gen = os.path.join(shapes_root, "gen_wrapper")

        self.assertTrue(os.path.isdir(shapes_root))
        self.assertTrue(os.path.isdir(shapes_src))
        self.assertTrue(os.path.isdir(wrapper_root_ref))

        generate_script = os.path.abspath("cppwg/__main__.py")
        package_info_path = os.path.join(wrapper_root_ref, "package_info.yaml")
        self.assertTrue(os.path.isfile(package_info_path))

        includes = " ".join(glob(shapes_src + "/*/"))

        # Generate the wrappers
        subprocess.call(
            [
                "python",
                generate_script,
                shapes_src,
                "--wrapper_root",
                wrapper_root_gen,
                "--package_info",
                package_info_path,
                "--includes",
                includes,
            ]
        )

        self.assertTrue(os.path.isdir(wrapper_root_gen))

        # Compare the generated files with reference files
        for dirpath, _, filenames in os.walk(wrapper_root_ref):
            for filename in filenames:
                if filename.endswith(".cppwg.cpp") or filename.endswith(".cppwg.hpp"):
                    file_ref = os.path.join(dirpath, filename)
                    file_gen = file_ref.replace(wrapper_root_ref, wrapper_root_gen, 1)

                    self.assertTrue(os.path.isfile(file_ref))
                    self.assertTrue(os.path.isfile(file_gen))
                    self.assertTrue(compare_files(file_gen, file_ref))


if __name__ == "__main__":
    unittest.main()
