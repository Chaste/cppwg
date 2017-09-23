#include <pybind11/pybind11.h>
#include "wrapper_header_collection.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_pyshapes_math_funcs, m)
{
    m.def("add", &add, " " , py::arg("i") = 1., py::arg("j") = 2.);
}
