#include <pybind11/pybind11.h>
#include "wrapper_header_collection.hpp"
#include "Pet.cppwg.hpp"
#include "Dog.cppwg.hpp"
#include "units.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_py_example_project_functions, m)
{
    py::class_<QLength>(m, "QLength")
            .def(py::init<double>())
            .def(py::init<>());

    py::class_<QMass>(m, "QMass")
            .def(py::init<double>())
            .def(py::init<>());

    m.def("add", &add, " " , py::arg("i") = 1, py::arg("j") = 2);
    register_Pet_class(m);
    register_Dog_class(m);

    py::object py_kg = py::cast(kg);
    m.attr("kg") = py_kg;
}
