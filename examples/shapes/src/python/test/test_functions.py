import unittest

from pyshapes import math_funcs


class TestFunctions(unittest.TestCase):

    def testAdd(self):
        a = 4
        b = 5
        c = math_funcs.add(4, 5)
        self.assertTrue(c == a + b)


if __name__ == "__main__":
    unittest.main()
