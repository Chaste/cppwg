#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "wrapper_header_collection.hpp"

#include "Point2.cppwg.hpp"

namespace py = pybind11;
typedef Point<2 > Point2;
PYBIND11_DECLARE_HOLDER_TYPE(T, std::shared_ptr<T>);

void register_Point2_class(py::module &m){
py::class_<Point2  , std::shared_ptr<Point2 >   >(m, "Point2")
        .def(py::init< >())
        .def(py::init<double, double, double >(), py::arg("x"), py::arg("y"), py::arg("z") = 0.)
        .def(
            "GetLocation", 
            (::std::array<double, 2>(Point2::*)() const ) &Point2::GetLocation, 
            " "  )
        .def(
            "rGetLocation", 
            (::std::array<double, 2> const &(Point2::*)() const ) &Point2::rGetLocation, 
            " "  )
        .def(
            "GetIndex", 
            (unsigned int(Point2::*)() const ) &Point2::GetIndex, 
            " "  )
        .def(
            "SetIndex", 
            (void(Point2::*)(unsigned int)) &Point2::SetIndex, 
            " " , py::arg("index") )
        .def(
            "SetLocation", 
            (void(Point2::*)(::std::array<double, 2> const &)) &Point2::SetLocation, 
            " " , py::arg("rLocation") )
    ;
}
