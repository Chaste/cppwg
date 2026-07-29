# Bring in everything from the shared module
from pyshapes._syntax import TemplateClass
from pyshapes.geometry._pyshapes_geometry import *


class Point(TemplateClass):
    _instantiations = {
        2: Point_2,
        3: Point_3,
    }
