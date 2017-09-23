#include "../math_funcs/Pet.cppwg.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "wrapper_header_collection.hpp"

namespace py = pybind11;
typedef Pet Pet;
;

void register_Pet_class(py::module &m){
py::class_<Pet    >(m, "Pet")
        .def(py::init<::std::string const & >(), py::arg("rName") = "Dave")
        .def(
            "SetName", 
            (void(Pet::*)(::std::string const &)) &Pet::SetName, 
            " " , py::arg("rName"))
        .def(
            "rGetName", 
            (::std::string const &(Pet::*)() const ) &Pet::rGetName, 
            " " )
    ;
}
