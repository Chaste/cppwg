#include <pybind11/pybind11.h>
#include "wrapper_header_collection.hpp"
#include "Shape2.cppwg.hpp"
#include "Shape3.cppwg.hpp"
#include "Cuboid.cppwg.hpp"
#include "Rectangle.cppwg.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_pyshapes_primitives, m)
{
    register_Shape2_class(m);
    register_Shape3_class(m);
    register_Cuboid_class(m);
    register_Rectangle_class(m);
}
