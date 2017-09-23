import unittest
import py_example_project.functions


class TestClasses(unittest.TestCase):

    def testPet(self):

        name = 'Dave'
        dave = py_example_project.functions.Pet()
        self.failUnless(name == dave.rGetName())

        name = 'Molly'
        molly = py_example_project.functions.Pet(rName=name)
        self.failUnless(name == molly.rGetName())

        name2 = 'Charly'
        molly.SetName('Charly')
        self.failUnless(name2 == molly.rGetName())

    def testDog(self):

        name = 'Patch'
        patch = py_example_project.functions.Dog()
        self.failUnless(name == patch.rGetName())
        self.failUnless("Woof" == patch.Bark())


if __name__ == '__main__':
    unittest.main()