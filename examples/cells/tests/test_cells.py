import sys
import unittest

import petsc4py
import vtk
from pycells import MacroMesh, Node, PetscUtils, Scene


class TestCells(unittest.TestCase):
    def testMacroInstantiationFallback(self):
        # MacroMesh's explicit template instantiations are declared via a macro
        # (see MacroMesh.cpp), which cppwg's source-text scan cannot see. This
        # confirms the pygccxml discovery fallback wrapped MacroMesh<2, 2> and
        # MacroMesh<3, 3> so they are usable from Python.
        self.assertEqual(MacroMesh[2, 2]().GetDimension(), 2)
        self.assertEqual(MacroMesh[3, 3]().GetDimension(), 3)

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
        # Scene.ThrowException raises a C++ SimulationException (which, like
        # Chaste's Exception, derives from std::runtime_error and exposes
        # GetMessage()). The registered exception translator should surface it as
        # a Python RuntimeError rather than crashing the interpreter.
        with self.assertRaises(RuntimeError) as context:
            Scene[2].ThrowException()
        message = str(context.exception)
        self.assertIn("C++ exception thrown", message)
        # The translator uses GetMessage(), which prepends the file and line,
        # so the message differs from the default what() text. This confirms the
        # custom translator (not just pybind11's default) handled the exception.
        self.assertIn("Scene.cpp:", message)

    def testPetscError(self):
        # PETSc is a C library that reports errors with return codes. The
        # wrapper detects a bad PetscErrorCode and throws a std::runtime_error
        # (as PetscCallThrow would), which pybind11 surfaces as a Python
        # RuntimeError instead of letting the C error pass silently.
        with self.assertRaises(RuntimeError) as context:
            PetscUtils.ThrowPetscError()
        self.assertIn("PETSc returned error code", str(context.exception))


if __name__ == "__main__":
    unittest.main()
