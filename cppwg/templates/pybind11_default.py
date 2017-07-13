
class_cpp_header = """\
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
{includes}
#include "{class_short_name}.cppwg.hpp"

namespace py = pybind11;
typedef {class_full_name} {class_short_name};{smart_ptr_handle}
"""

class_hpp_header = """\
#ifndef {class_short_name}_hpp__pyplusplus_wrapper
#define {class_short_name}_hpp__pyplusplus_wrapper
namespace py = pybind11;
void register_{class_short_name}_class(py::module &m);
#endif // {class_short_name}_hpp__pyplusplus_wrapper
"""

class_virtual_override_header = """\
class {class_short_name}_Overloads : public {class_short_name}{{
    public:
    using {class_short_name}::{class_base_name};
"""

class_virtual_override_footer = "}\n"

class_definition = """\
void register_{short_name}_class(py::module &m){{
py::class_<{short_name} {overrides_string} {ptr_support} {bases} >(m, "{short_name}")
"""

method_virtual_override = """\
    {return_type} {method_name}({arg_string}){const_adorn} override {{
        PYBIND11_OVERLOAD{overload_adorn}(
            {tidy_method_name},
            {short_class_name},
            {method_name},
            {args_string});
    }}
"""

smart_pointer_holder = "PYBIND11_DECLARE_HOLDER_TYPE(T, {}<T>)"

free_function = """\
    m.def{def_adorn}("{function_name}", &{function_name}, {function_docs} {default_args});
"""

class_method = """\
        .def{def_adorn}(
            "{method_name}", 
            ({return_type}({self_ptr})({arg_signature}){const_adorn}) &{class_short_name}::{method_name}, 
            {method_docs} {default_args} {call_policy})
"""

template_collection = {'class_cpp_header': class_cpp_header,
                       'free_function': free_function,
                       'class_hpp_header': class_hpp_header,
                       'class_method': class_method,
                       'class_definition': class_definition,
                       'class_virtual_override_header': class_virtual_override_header,
                       'class_virtual_override_footer': class_virtual_override_footer,
                       'smart_pointer_holder': smart_pointer_holder,
                       'method_virtual_override': method_virtual_override}
