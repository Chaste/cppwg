#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "wrapper_header_collection.hpp"

#include "Shape3.cppwg.hpp"

namespace py = pybind11;
typedef Shape<3 > Shape3;
PYBIND11_DECLARE_HOLDER_TYPE(T, std::shared_ptr<T>);

void register_Shape3_class(py::module &m){
py::class_<Shape3  , std::shared_ptr<Shape3 >   >(m, "Shape3")
        .def(py::init< >())
        .def(
            "GetIndex",
            (unsigned int(Shape3::*)() const ) &Shape3::GetIndex,
            " "  )
        .def(
            "rGetVertices",
            (::std::vector<std::shared_ptr<Point<3>>> const &(Shape3::*)() const ) &Shape3::rGetVertices,
            " "  )
        .def(
            "SetIndex",
            (void(Shape3::*)(unsigned int)) &Shape3::SetIndex,
            " " , py::arg("index") )
        .def(
            "SetVertices",
            (void(Shape3::*)(::std::vector<std::shared_ptr<Point<3>>> const &)) &Shape3::SetVertices,
            " " , py::arg("rVertices") )
    ;
}
