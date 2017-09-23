#ifndef Dog_hpp__pyplusplus_wrapper
#define Dog_hpp__pyplusplus_wrapper
namespace py = pybind11;
void register_Dog_class(py::module &m);
#endif // Dog_hpp__pyplusplus_wrapper
