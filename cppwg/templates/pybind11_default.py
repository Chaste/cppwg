from string import Template

from cppwg.utils.constants import CPPWG_CLASS_OVERRIDE_SUFFIX, CPPWG_EXT

class_cpp_header = """\
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
{includes}
#include "{class_py_name}.%s.hpp"

namespace py = pybind11;
typedef {class_cpp_name} {class_py_name};
{smart_ptr_handle};
""" % CPPWG_EXT

class_cpp_header_chaste = """\
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
{includes}
//#include "PythonObjectConverters.hpp"
#include "{class_py_name}.%s.hpp"

namespace py = pybind11;
//PYBIND11_CVECTOR_TYPECASTER2();
//PYBIND11_CVECTOR_TYPECASTER3();
typedef {class_cpp_name} {class_py_name};
{smart_ptr_handle};
""" % CPPWG_EXT

class_hpp_header = """\
#ifndef {class_py_name}_hpp__%s_wrapper
#define {class_py_name}_hpp__%s_wrapper

#include <pybind11/pybind11.h>

void register_{class_py_name}_class(pybind11::module &m);
#endif // {class_py_name}_hpp__%s_wrapper
""" % tuple([CPPWG_EXT]*3)

class_virtual_override_header = """\
class {class_py_name}%s : public {class_py_name}
{{
public:
    using {class_py_name}::{class_base_name};
""" % CPPWG_CLASS_OVERRIDE_SUFFIX

class_virtual_override_footer = "}\n"

class_definition = """\
void register_{class_py_name}_class(py::module &m)
{{
    py::class_<{class_py_name}{overrides_string}{ptr_support}{bases}>(m, "{class_py_name}")
"""

method_virtual_override = """\
    {return_type} {method_name}({arg_string}){const_adorn} override
    {{
        PYBIND11_OVERRIDE{overload_adorn}(
            {tidy_method_name},
            {class_py_name},
            {method_name},
            {args_string});
    }}
"""

smart_pointer_holder = "PYBIND11_DECLARE_HOLDER_TYPE(T, {}<T>)"

free_function = """\
    m.def{def_adorn}("{function_name}", &{function_name}, {function_docs}{default_args});
"""

class_method = """\
        .def{def_adorn}("{method_name}",
            ({return_type}({self_ptr})({arg_signature}){const_adorn}) &{class_py_name}::{method_name},
            {method_docs}{default_args}{call_policy})
"""

# Skeleton for a module's main cpp file. The writer builds each ${block}
# (includes, register calls, etc.) and fills this template.
module_main_cpp = Template(
    "${prefix_text}"
    "#include <pybind11/pybind11.h>\n"
    "${includes}"
    "${module_pre_code}"
    "${class_includes}"
    "\n"
    "namespace py = pybind11;\n"
    "\n"
    "PYBIND11_MODULE(${full_module_name}, m)\n"
    "{\n"
    "${imports}"
    "${exception_translator}"
    "${free_functions}"
    "${register_calls}"
    "${module_code}"
    "}\n"
)

template_collection = {
    "module_main_cpp": module_main_cpp,
    "class_cpp_header": class_cpp_header,
    "free_function": free_function,
    "class_hpp_header": class_hpp_header,
    "class_method": class_method,
    "class_definition": class_definition,
    "class_virtual_override_header": class_virtual_override_header,
    "class_virtual_override_footer": class_virtual_override_footer,
    "smart_pointer_holder": smart_pointer_holder,
    "method_virtual_override": method_virtual_override,
}
