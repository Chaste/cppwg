from string import Template

from cppwg.utils.constants import CPPWG_CLASS_OVERRIDE_SUFFIX, CPPWG_EXT

class_virtual_override_header = """\
class {class_py_name}%s : public {class_py_name}
{{
public:
    using {class_py_name}::{class_base_name};
""" % CPPWG_CLASS_OVERRIDE_SUFFIX

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

class_constructor = """\
        .def(py::init<{arg_signature}>(){default_args})
"""

# Consolidated whole-file skeletons. The writer builds each ${block} (includes,
# constructors, methods, etc.) and fills the skeleton in a single substitution,
# so the shape of the generated file is visible here rather than reconstructed
# from concatenation in the writer. These use string.Template ($ placeholders)
# so literal C++ braces need no escaping.

# Skeleton for a module's main cpp file.
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

# Skeleton for a class wrapper hpp file.
class_hpp = Template(
    "${prefix_text}"
    "#ifndef ${class_py_name}_hpp__" + CPPWG_EXT + "_wrapper\n"
    "#define ${class_py_name}_hpp__" + CPPWG_EXT + "_wrapper\n"
    "\n"
    "#include <pybind11/pybind11.h>\n"
    "\n"
    "void register_${class_py_name}_class(pybind11::module &m);\n"
    "#endif // ${class_py_name}_hpp__" + CPPWG_EXT + "_wrapper\n"
)

# Skeleton for a class wrapper cpp file.
class_cpp = Template(
    "${prefix_text}"
    "#include <pybind11/pybind11.h>\n"
    "#include <pybind11/stl.h>\n"
    "${includes}"
    "\n"
    '#include "${class_py_name}.' + CPPWG_EXT + '.hpp"\n'
    "\n"
    "namespace py = pybind11;\n"
    "typedef ${class_cpp_name} ${class_py_name};\n"
    "${smart_ptr_handle};\n"
    "${prefix_code}"
    "${generator_pre_code}"
    "${return_typedefs}"
    "\n"
    "${override_class}"
    "void register_${class_py_name}_class(py::module &m)\n"
    "{\n"
    '    py::class_<${class_py_name}${overrides_string}${ptr_support}${bases}>'
    '(m, "${class_py_name}")\n'
    "${constructors}"
    "${methods}"
    "${generator_def_code}"
    "${suffix_code}"
    "    ;\n"
    "}\n"
)

# Skeleton for the struct-enum special case, e.g.:
#   struct Foo { enum Value { A, B, C }; };
# The header block is identical to a class cpp file; the registration body wraps
# the single nested enum. Uses the raw C++ decl name for registration.
struct_enum_cpp = Template(
    "${prefix_text}"
    "#include <pybind11/pybind11.h>\n"
    "#include <pybind11/stl.h>\n"
    "${includes}"
    "\n"
    '#include "${class_py_name}.' + CPPWG_EXT + '.hpp"\n'
    "\n"
    "namespace py = pybind11;\n"
    "typedef ${class_cpp_name} ${class_py_name};\n"
    "${smart_ptr_handle};\n"
    "${prefix_code}"
    "${generator_pre_code}"
    "void register_${class_name}_class(py::module &m){\n"
    '    py::class_<${class_name}> myclass(m, "${class_name}");\n'
    '    py::enum_<${class_name}::${enum_name}>(myclass, "${enum_name}")\n'
    "${enum_values}"
    "    .export_values();\n"
    "}\n"
)

# Skeleton for the header collection hpp file, which includes every header to be
# parsed by CastXML plus the explicit template instantiations and typedefs
# (e.g. typedef Foo<2,2> Foo_2_2) for all classes to be wrapped.
header_collection_hpp = Template(
    "${prefix_text}"
    "#ifndef ${guard}\n"
    "#define ${guard}\n"
    "\n"
    "// Includes\n"
    "${includes}"
    "\n"
    "// Instantiate Template Classes\n"
    "${template_instantiations}"
    "\n"
    "// Typedefs for nicer naming\n"
    "namespace cppwg\n"
    "{\n"
    "${template_typedefs}"
    "} // namespace cppwg\n"
    "\n"
    "#endif // ${guard}\n"
)

template_collection = {
    "module_main_cpp": module_main_cpp,
    "header_collection_hpp": header_collection_hpp,
    "class_hpp": class_hpp,
    "class_cpp": class_cpp,
    "struct_enum_cpp": struct_enum_cpp,
    "free_function": free_function,
    "class_method": class_method,
    "class_constructor": class_constructor,
    "class_virtual_override_header": class_virtual_override_header,
    "smart_pointer_holder": smart_pointer_holder,
    "method_virtual_override": method_virtual_override,
}
