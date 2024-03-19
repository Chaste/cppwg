#include <pybind11/pybind11.h>
#include "wrapper_header_collection.hpp"
#include "Point2.cppwg.hpp"
#include "Point3.cppwg.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_pyshapes_geometry, m)
{
    register_Point2_class(m);
    register_Point3_class(m);
}
