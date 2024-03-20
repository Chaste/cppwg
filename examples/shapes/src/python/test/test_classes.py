import unittest
import pyshapes.geometry
import pyshapes.primitives


class TestClasses(unittest.TestCase):

    def testGeometry(self):

        p1 = pyshapes.geometry.Point2(0.0, 0.0)
        p2 = pyshapes.geometry.Point2(1.0, 0.0)
        p3 = pyshapes.geometry.Point2(0.0, 1.0)
        points = [p1, p2, p3]
        triangle = pyshapes.primitives.Shape2()
        triangle.SetVertices(points)
        self.assertTrue(len(triangle.rGetVertices()) == 3)

        rectangle = pyshapes.primitives.Rectangle(5.0, 10.0)
        self.assertTrue(len(rectangle.rGetVertices()) == 4)

        cuboid = pyshapes.primitives.Cuboid(5.0, 10.0, 20.0)
        self.assertTrue(len(cuboid.rGetVertices()) == 8)


if __name__ == "__main__":
    unittest.main()
