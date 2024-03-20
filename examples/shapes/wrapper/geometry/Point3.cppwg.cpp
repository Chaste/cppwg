#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "wrapper_header_collection.hpp"

#include "Point3.cppwg.hpp"

namespace py = pybind11;
typedef Point<3 > Point3;
PYBIND11_DECLARE_HOLDER_TYPE(T, std::shared_ptr<T>);

void register_Point3_class(py::module &m){
py::class_<Point3  , std::shared_ptr<Point3 >   >(m, "Point3")
        .def(py::init< >())
        .def(py::init<double, double, double >(), py::arg("x"), py::arg("y"), py::arg("z") = 0.)
        .def(
            "GetLocation",
            (::std::array<double, 3>(Point3::*)() const ) &Point3::GetLocation,
            " "  )
        .def(
            "rGetLocation",
            (::std::array<double, 3> const &(Point3::*)() const ) &Point3::rGetLocation,
            " "  )
        .def(
            "GetIndex",
            (unsigned int(Point3::*)() const ) &Point3::GetIndex,
            " "  )
        .def(
            "SetIndex",
            (void(Point3::*)(unsigned int)) &Point3::SetIndex,
            " " , py::arg("index") )
        .def(
            "SetLocation",
            (void(Point3::*)(::std::array<double, 3> const &)) &Point3::SetLocation,
            " " , py::arg("rLocation") )
    ;
}
