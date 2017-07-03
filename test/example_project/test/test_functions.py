import unittest

import py_example_project.functions


def main():
    unittest.main()


class TestFunctions(unittest.TestCase):

    def testAdd(self):
        a = 4
        b = 5
        c = py_example_project.functions.add(4, 5)
        self.failUnless(c == a + b)


if __name__ == '__main__':
    main()