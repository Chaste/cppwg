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
        # GetAreaInSquareMetres / GetAreaInSquareFeet. The TemplateMethod
        # descriptor exposes the C++-like subscript form GetAreaIn[UNIT]().
        prim = pyshapes.primitives
        square = prim.UnitSquare(3.0)  # side 3 -> 9 square metres

        self.assertEqual(square.GetAreaIn[prim.SquareMetres](), 9.0)
        self.assertAlmostEqual(square.GetAreaIn[prim.SquareFeet](), 96.8752, places=4)
        # The subscript form is exactly the mangled binding.
        self.assertEqual(
            square.GetAreaIn[prim.SquareFeet](), square.GetAreaInSquareFeet()
        )


if __name__ == "__main__":
    unittest.main()
