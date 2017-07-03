import unittest

import py_example_project.functions


def main():
    unittest.main()


class TestFunctions(unittest.TestCase):

    def testAdd(self):
        a = 4
        b = 5
        c = py_example_project.functions.add(i=4, j=5)
        self.failUnless(c == a + b)

        # Test default args
        c = py_example_project.functions.add()
        self.failUnless(c == 3)


if __name__ == '__main__':
    main()