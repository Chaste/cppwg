# Bring in everything from the shared module
from pyshapes._syntax import TemplateClass, TemplateMethod
from pyshapes.primitives._pyshapes_primitives import *


class Shape(TemplateClass):
    _instantiations = {
        2: Shape_2,
        3: Shape_3,
    }


# UnitSquare::GetAreaIn<UNIT>() is a templated method (see GetAreaInCustomTemplate.py);
# expose its per-unit bindings as GetAreaIn[Unit]().
UnitSquare.GetAreaIn = TemplateMethod("GetAreaIn")
