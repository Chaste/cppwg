import unittest

from pyshapes import math_funcs


class TestFunctions(unittest.TestCase):
    def testAdd(self):
        a = 4
        b = 5
        c = math_funcs.add(4, 5)
        self.assertTrue(c == a + b)

    def testExceptionTranslation(self):
        # The C++ function throws a ShapeException (which does not derive from
        # std::exception). The registered exception translator should surface it
        # as a Python RuntimeError rather than crashing the interpreter.
        with self.assertRaises(RuntimeError) as context:
            math_funcs.throw_exception()
        self.assertEqual(str(context.exception), "C++ exception thrown")


if __name__ == "__main__":
    unittest.main()
