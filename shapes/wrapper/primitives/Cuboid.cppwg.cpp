#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "wrapper_header_collection.hpp"

#include "Cuboid.cppwg.hpp"

namespace py = pybind11;
typedef Cuboid Cuboid;
PYBIND11_DECLARE_HOLDER_TYPE(T, std::shared_ptr<T>);

void register_Cuboid_class(py::module &m){
py::class_<Cuboid  , std::shared_ptr<Cuboid >  , Shape<3>  >(m, "Cuboid")
        .def(py::init<double, double, double >(), py::arg("width") = 2., py::arg("height") = 1., py::arg("depth") = 1.)
    ;
}
