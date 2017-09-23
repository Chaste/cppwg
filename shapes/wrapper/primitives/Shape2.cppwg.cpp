#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "wrapper_header_collection.hpp"

#include "Shape2.cppwg.hpp"

namespace py = pybind11;
typedef Shape<2 > Shape2;
PYBIND11_DECLARE_HOLDER_TYPE(T, std::shared_ptr<T>);

void register_Shape2_class(py::module &m){
py::class_<Shape2  , std::shared_ptr<Shape2 >   >(m, "Shape2")
        .def(py::init< >())
        .def(
            "GetIndex", 
            (unsigned int(Shape2::*)() const ) &Shape2::GetIndex, 
            " "  )
        .def(
            "rGetVertices", 
            (::std::vector<std::shared_ptr<Point<2> >, std::allocator<std::shared_ptr<Point<2> > > > const &(Shape2::*)() const ) &Shape2::rGetVertices, 
            " "  )
        .def(
            "SetIndex", 
            (void(Shape2::*)(unsigned int)) &Shape2::SetIndex, 
            " " , py::arg("index") )
        .def(
            "SetVertices", 
            (void(Shape2::*)(::std::vector<std::shared_ptr<Point<2> >, std::allocator<std::shared_ptr<Point<2> > > > const &)) &Shape2::SetVertices, 
            " " , py::arg("rVertices") )
    ;
}
