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

    def testUnwrappedException(self):
        # throw_unwrapped_exception raises a C++ type that is not listed under
        # `exceptions`, so cppwg generates no translator for it. pybind11 still
        # surfaces it as a generic RuntimeError rather than letting it escape.
        with self.assertRaises(RuntimeError) as context:
            math_funcs.throw_unwrapped_exception()
        self.assertEqual(str(context.exception), "Caught an unknown exception!")


if __name__ == "__main__":
    unittest.main()
