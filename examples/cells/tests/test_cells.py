import sys
import unittest

import petsc4py
import vtk
from pycells import (
    Cell,
    CellFactory,
    Corner,
    Facet,
    MacroMesh,
    MeshFactory,
    Node,
    PetscUtils,
    PottsMesh,
    Scene,
    SphericalMesh,
)


class TestCells(unittest.TestCase):
    def testCuratedBoundaryElement(self):
        # Facet<2> is safe to wrap: its faces Facet<1> are instantiated. Wrapping
        # the low-dim Facet<1> instead would reference the never-instantiated
        # Facet<0> and break the import (see Facet.hpp). This confirms the
        # curated case imports and works.
        self.assertEqual(Facet[2]().GetNumFaces(), 0)

    def testNonCuratedBoundaryElement(self):
        # Corner is the non-curated counterpart to Facet: same structure
        # (Corner<0> is never instantiated), but resolved by cppwg's automatic
        # pruning instead of a template_substitutions block. Discovery finds
        # Corner<1> and Corner<2>; Corner<1> is auto-dropped (its GetSub returns
        # the never-instantiated Corner<0>), leaving Corner<2> usable.
        self.assertEqual(Corner[2]().GetNumSubs(), 0)
        # Corner<1> was dropped, so it is not available.
        with self.assertRaises(KeyError):
            _ = Corner[1]

    def testAutoIncludeTemplateArg(self):
        # CellFactory<CELL_TYPE, DIM> names CELL_TYPE (Cell) only as a template
        # argument - never in a wrapped signature - mirroring pychaste's
        # CellsGenerator<CELL_CYCLE_MODEL, DIM>. auto_includes resolved Cell.hpp
        # from the instantiation arguments so the wrapper compiled at all; this
        # confirms the instantiations import and work.
        factory = CellFactory[Cell, 2]()
        self.assertEqual(factory.GetDimension(), 2)
        self.assertEqual(factory.CreateCell(), 1)
        self.assertEqual(factory.CreateCell(), 2)
        self.assertEqual(CellFactory[Cell, 3]().GetDimension(), 3)

    def testMacroInstantiationFallback(self):
        # MacroMesh's explicit template instantiations are declared via a macro
        # (see MacroMesh.cpp), which cppwg's source-text scan cannot see. This
        # confirms the pygccxml discovery fallback wrapped MacroMesh<2, 2> and
        # MacroMesh<3, 3> so they are usable from Python.
        self.assertEqual(MacroMesh[2, 2]().GetDimension(), 2)
        self.assertEqual(MacroMesh[3, 3]().GetDimension(), 3)

    def testNestedTemplateArgSubscript(self):
        # MeshFactory<MESH> has a single template argument that is itself a
        # templated type - MeshFactory<PottsMesh<2>>. It is subscripted with the
        # Python mesh class, MeshFactory[PottsMesh[2]] (PottsMesh[2] is the
        # PottsMesh_2 class), rather than splitting the argument as
        # MeshFactory[PottsMesh, 2].
        factory = MeshFactory[PottsMesh[2]]()
        self.assertIsInstance(factory.generateMesh(), PottsMesh[2])
        self.assertIsInstance(MeshFactory[PottsMesh[3]]().generateMesh(), PottsMesh[3])
        # The split-argument form is not a valid key.
        with self.assertRaises(KeyError):
            _ = MeshFactory[PottsMesh, 2]

    def testInheritedOverrideStillCallable(self):
        # SphericalMesh is the concrete leaf of an abstract chain
        # (AbstractMesh -> AbstractSphericalMesh -> SphericalMesh). Its
        # Scale and GetNumElements overrides are skipped on the leaf wrapper by
        # exclude_inherited_overrides, but the bindings on the abstract bases
        # make them - and the other inherited members - callable on instances.
        mesh = SphericalMesh[2, 2]()
        self.assertEqual(mesh.GetNumElements(), 0)  # AbstractSphericalMesh
        mesh.Scale(2.0)  # AbstractMesh (pure virtual, overridden in leaf)
        mesh.SetIndex(7)  # AbstractMesh (non-virtual)
        self.assertEqual(mesh.GetIndex(), 7)
        self.assertEqual(SphericalMesh[3, 3]().GetNumElements(), 0)

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
        # Scene.ThrowException raises a C++ SimulationException (which derives
        # from std::runtime_error and exposes GetMessage()). The registered
        # exception translator should surface it as a Python RuntimeError rather
        # than crashing the interpreter.
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
