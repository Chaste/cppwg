# Bring in everything from the shared module
from pyshapes._syntax import TemplateClassDict, TemplateMethod
from pyshapes.primitives._pyshapes_primitives import *

Shape = TemplateClassDict(
    {
        2: Shape_2,
        3: Shape_3,
    }
)

# UnitSquare::GetAreaIn<UNIT>() is a templated method; cppwg emitted one binding
# per unit (GetAreaInSquareMetres, ...). Expose them with subscript syntax so
# square.GetAreaIn[SquareFeet]() calls square.GetAreaInSquareFeet().
UnitSquare.GetAreaIn = TemplateMethod("GetAreaIn")
