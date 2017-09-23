#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "wrapper_header_collection.hpp"
#include "Dog.cppwg.hpp"

namespace py = pybind11;
typedef Dog Dog;
;

void register_Dog_class(py::module &m){
py::class_<Dog   , Pet  >(m, "Dog")
        .def(py::init<::std::string const & >(), py::arg("rName") = "Patch")
        .def(
            "Bark", 
            (::std::string(Dog::*)() const ) &Dog::Bark, 
            " " )
    ;
}
