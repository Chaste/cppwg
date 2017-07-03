#include <pybind11/pybind11.h>
#include "wrapper_header_collection.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_py_example_project_functions, m)
{
    m.def("add", &add, "");
}
