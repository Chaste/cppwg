import sys
import unittest

import petsc4py
import vtk
from pycells import Node, PetscUtils, Scene


class TestCells(unittest.TestCase):
    def testVtkCaster(self):
        scene = Scene[2]()
        renderer = scene.GetRenderer()
        self.assertIsNotNone(renderer)

    def testPetscCaster(self):
        petsc4py.init(sys.argv)
        vec = PetscUtils.CreateVec(10)
        self.assertIsNotNone(vec)

    def testUblasCaster(self):
        node = Node[2]()
        self.assertEqual(list(node.GetLocation()), [0, 0])
        node.Translate([1, 1])
        self.assertEqual(list(node.GetLocation()), [1, 1])

    def testExceptionTranslation(self):
        # ThrowException raises a C++ SimulationException (which, like Chaste's
        # Exception, derives from std::runtime_error and exposes GetMessage()).
        # The registered exception translator should surface it as a Python
        # RuntimeError rather than crashing the interpreter.
        with self.assertRaises(RuntimeError) as context:
            PetscUtils.ThrowException()
        message = str(context.exception)
        self.assertIn("C++ exception thrown", message)
        # The translator uses GetMessage(), which prepends the file and line,
        # so the message differs from the default what() text. This confirms the
        # custom translator (not just pybind11's default) handled the exception.
        self.assertIn("PetscUtils.cpp:", message)


if __name__ == "__main__":
    unittest.main()
