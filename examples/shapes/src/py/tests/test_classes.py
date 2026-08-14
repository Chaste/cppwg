import inspect
import unittest

import pyshapes.composites
import pyshapes.geometry
import pyshapes.primitives


class TestClasses(unittest.TestCase):
    def testGeometry(self):
        p0 = pyshapes.geometry.Point_2()
        self.assertTrue(p0.GetLocation() == [0.0, 0.0])

        p1 = pyshapes.geometry.Point_2(5.0, 0.0)
        self.assertTrue(p1.GetLocation() == [5.0, 0.0])

        p2 = pyshapes.geometry.Point_2(5.0, 5.0)
        self.assertTrue(p2.GetLocation() == [5.0, 5.0])

        p3 = pyshapes.geometry.Point_2(0.0, 5.0)
        self.assertTrue(p3.GetLocation() == [0.0, 5.0])

        points = [p1, p2, p3]

        triangle = pyshapes.primitives.Shape_2()
        triangle.SetVertices(points)
        self.assertTrue(len(triangle.rGetVertices()) == 3)

        rectangle = pyshapes.primitives.Rectangle(5.0, 10.0)
        self.assertTrue(len(rectangle.rGetVertices()) == 4)

        rectangle = pyshapes.primitives.Rectangle([p0, p1, p2, p3])
        self.assertTrue(rectangle.rGetVertices() == [p0, p1, p2, p3])

        cuboid = pyshapes.primitives.Cuboid(5.0, 10.0, 20.0)
        self.assertTrue(len(cuboid.rGetVertices()) == 8)

    def testCrossModuleInheritance(self):
        # Square is wrapped in the `composites` module, but inherits Rectangle
        # which is wrapped in the separate `primitives` module. This checks that
        # the cross-module inheritance is linked: a Square is a Rectangle, and
        # the inherited Rectangle/Shape interface is available on it.
        square = pyshapes.composites.Square(5.0)
        self.assertTrue(isinstance(square, pyshapes.primitives.Rectangle))
        self.assertTrue(len(square.rGetVertices()) == 4)

    def testSyntax(self):
        # Point is a real class exposing __class_getitem__ (like list[int]), so
        # Point[dim] resolves the concrete instantiation.
        self.assertTrue(inspect.isclass(pyshapes.geometry.Point))
        self.assertEqual(pyshapes.geometry.Point[2], pyshapes.geometry.Point_2)

        point = pyshapes.geometry.Point[3](0.0, 1.0, 2.0)
        self.assertTrue(point.GetLocation() == [0.0, 1.0, 2.0])

    def testTemplateMethodSyntax(self):
        # UnitSquare::GetAreaIn<UNIT>() is a templated method wrapped per unit as
        # GetAreaIn_SquareMetres / GetAreaIn_SquareFeet. The TemplateMethod
        # descriptor exposes the C++-like subscript form GetAreaIn[UNIT]().
        prim = pyshapes.primitives
        square = prim.UnitSquare(3.0)  # side 3 -> 9 square metres

        self.assertEqual(square.GetAreaIn[prim.SquareMetres](), 9.0)
        self.assertAlmostEqual(square.GetAreaIn[prim.SquareFeet](), 96.8752, places=4)
        # The subscript form is exactly the mangled binding.
        self.assertEqual(
            square.GetAreaIn[prim.SquareFeet](), square.GetAreaIn_SquareFeet()
        )

    def testTemplateMethodFallback(self):
        # GetAreaIn is also a plain (non-templated) overload,
        # GetAreaIn(perSquareMetre). The TemplateMethod descriptor would shadow it,
        # but it was passed as the fallback, so calling GetAreaIn without a
        # subscript dispatches to the plain overload.
        prim = pyshapes.primitives
        square = prim.UnitSquare(3.0)  # side 3 -> 9 square metres

        # Plain call (no subscript) -> the C++ GetAreaIn(double) overload.
        self.assertAlmostEqual(square.GetAreaIn(10.7639104), 96.8752, places=4)
        # It agrees with the templated form when given that unit's factor.
        self.assertEqual(square.GetAreaIn(1.0), square.GetAreaIn[prim.SquareMetres]())

        # Class-level access supplies the receiver explicitly, so the descriptor
        # must not inject it again: UnitSquare.GetAreaIn(square, factor) behaves
        # like the unbound plain overload.
        self.assertEqual(prim.UnitSquare.GetAreaIn(square, 1.0), square.GetAreaIn(1.0))

    def testEnums(self):
        # ShapeKind is a plain (unscoped) enum wrapped as a first-class entity.
        # Being unscoped, .export_values() also exposes the enumerators directly.
        prim = pyshapes.primitives
        self.assertEqual(int(prim.ShapeKind.CIRCLE), 0)
        self.assertEqual(int(prim.ShapeKind.TRIANGLE), 2)
        # Unscoped: .export_values() also exposes the enumerators at module scope.
        self.assertEqual(prim.CIRCLE, prim.ShapeKind.CIRCLE)

        # Handedness is a scoped enum (enum class); enumerators live on the type.
        self.assertEqual(int(prim.Handedness.RIGHT), 1)
        # Scoped enums do not export their enumerators into the enclosing scope,
        # so LEFT/RIGHT are not module-level names (no .export_values()).
        self.assertFalse(hasattr(prim, "LEFT"))
        self.assertFalse(hasattr(prim, "RIGHT"))

        # ShapeClassifier.Describe takes ShapeKind as a defaulted argument. That
        # the module imported at all proves the enum was registered before this
        # class (pybind11 materialises the default at registration time). Check
        # both the default and an explicit enum value are accepted.
        classifier = prim.ShapeClassifier()
        self.assertEqual(classifier.Describe(), "circle")
        self.assertEqual(classifier.Describe(prim.ShapeKind.SQUARE), "square")
        self.assertEqual(classifier.GetHandedness(), prim.Handedness.RIGHT)

    def testExcludedAbstractBases(self):
        # AbstractShape / AbstractPolygon are listed in the layout's `exclude`, so
        # they are held out of the Python package namespace (neither the template
        # stubs nor the concrete instantiations are exposed).
        prim = pyshapes.primitives
        for name in ("AbstractShape", "AbstractPolygon"):
            self.assertFalse(hasattr(prim, name))
            self.assertFalse(hasattr(prim, name + "_2"))
            self.assertFalse(hasattr(prim, name + "_3"))

        # They stay registered in the compiled extension, though: RegularPolygon
        # is concrete and exposed, and (via exclude_inherited_overrides) inherits
        # GetArea/GetNumSides from those hidden bases, so it is fully usable.
        hexagon = prim.RegularPolygon[2](6, 2.0)
        self.assertEqual(hexagon.GetNumSides(), 6)
        self.assertEqual(hexagon.GetArea(), 0.25 * 6 * 2.0 * 2.0)

    def testStructDataMembers(self):
        # ShapeMetrics is a plain data struct wrapped as a normal class (#116).
        prim = pyshapes.primitives
        metrics = prim.ShapeMetrics()

        # Mutable members are exposed read/write with def_readwrite.
        metrics.area = 3.0
        metrics.perimeter = 7.5
        self.assertEqual(metrics.area, 3.0)
        self.assertEqual(metrics.perimeter, 7.5)

        # The const member is read-only (def_readonly); assigning it raises.
        self.assertEqual(metrics.dimension, 2)
        with self.assertRaises(AttributeError):
            metrics.dimension = 3

        # The `scratch` field is suppressed via excluded_variables.
        self.assertFalse(hasattr(metrics, "scratch"))


if __name__ == "__main__":
    unittest.main()
