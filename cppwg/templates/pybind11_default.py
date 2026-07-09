from string import Template

from cppwg.utils.constants import CPPWG_CLASS_OVERRIDE_SUFFIX, CPPWG_EXT

# Item-level fragments, rendered per-item by the writers and joined into the
# blocks that fill the whole-file skeletons below. Like the skeletons, these use
# string.Template ($ placeholders) so literal C++ braces need no escaping, and so
# every entry in template_collection is filled the same way (via .substitute).

class_virtual_override_header = Template(
    "class ${class_py_name}" + CPPWG_CLASS_OVERRIDE_SUFFIX + " : public ${class_py_name}\n"
    "{\n"
    "public:\n"
    "    using ${class_py_name}::${class_base_name};\n"
)

method_virtual_override = Template(
    "    ${return_type} ${method_name}(${arg_string})${const_adorn} override\n"
    "    {\n"
    "        PYBIND11_OVERRIDE${overload_adorn}(\n"
    "            ${tidy_method_name},\n"
    "            ${class_py_name},\n"
    "            ${method_name},\n"
    "            ${args_string});\n"
    "    }\n"
)

smart_pointer_holder = Template("PYBIND11_DECLARE_HOLDER_TYPE(T, ${holder}<T>)")

free_function = Template(
    '    m.def${def_adorn}("${function_name}", &${function_name}, '
    "${function_docs}${default_args});\n"
)

class_method = Template(
    '        .def${def_adorn}("${method_name}",\n'
    "            (${return_type}(${self_ptr})(${arg_signature})${const_adorn})"
    " &${class_py_name}::${method_name},\n"
    "            ${method_docs}${default_args}${call_policy})\n"
)

class_constructor = Template(
    "        .def(py::init<${arg_signature}>()${default_args})\n"
)

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

# A pybind11 exception translator for a module's ${exception_translator} block,
# with one ${catch_clauses} entry (module_exception_catch) per configured
# exception class. Each catch clause opens with `}` to close the preceding try
# or catch block.
module_exception_translator = Template(
    "    py::register_exception_translator([](std::exception_ptr p) {\n"
    "        try {\n"
    "            if (p) std::rethrow_exception(p);\n"
    "${catch_clauses}"
    "        }\n"
    "    });\n"
    "\n"
)

module_exception_catch = Template(
    "        } catch (const ${cpp_type}& e) {\n"
    "            PyErr_SetString(PyExc_RuntimeError, ${message_expr});\n"
)

# Skeleton for a class wrapper hpp file.
# Skeleton for a class wrapper hpp file. One hpp is emitted per class (not per
# template instantiation); it forward-declares the register function for every
# instantiation via ${register_declarations}.
class_hpp = Template(
    "${prefix_text}"
    "#ifndef ${class_hpp_name}_hpp__" + CPPWG_EXT + "_wrapper\n"
    "#define ${class_hpp_name}_hpp__" + CPPWG_EXT + "_wrapper\n"
    "\n"
    "#include <pybind11/pybind11.h>\n"
    "\n"
    "${register_declarations}"
    "#endif // ${class_hpp_name}_hpp__" + CPPWG_EXT + "_wrapper\n"
)

# A single register-function forward declaration, one per instantiation, joined
# into ${register_declarations} above.
class_hpp_register_declaration = Template(
    "void register_${class_py_name}_class(pybind11::module &m);\n"
)

# Preamble for a class wrapper cpp file, emitted once per class. The file-scope
# items that must appear only once when several instantiations share a file live
# here: the includes, the smart-pointer holder declaration, class-level prefix
# code, and the (deduplicated) trampoline return typedefs. Each instantiation's
# registration follows via one class_cpp_register block.
class_cpp_header = Template(
    "${prefix_text}"
    "#include <pybind11/pybind11.h>\n"
    "#include <pybind11/stl.h>\n"
    "${includes}"
    "\n"
    '#include "${class_hpp_name}.' + CPPWG_EXT + '.hpp"\n'
    "\n"
    "namespace py = pybind11;\n"
    "${smart_ptr_handle};\n"
    "${prefix_code}"
    "${return_typedefs}"
)

# Registration block for one template instantiation, appended once per
# instantiation after the class_cpp_header preamble. Refers to the class through
# the wrapper alias (class_py_name, typedef'd to the C++ type) so the trampoline,
# registration function name and Python-visible name all match.
class_cpp_register = Template(
    "${generator_pre_code}"
    "typedef ${class_cpp_name} ${class_py_name};\n"
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
# The registration body wraps the single nested enum. Like class_cpp_register it
# refers to the class through the wrapper alias (class_py_name), and follows the
# shared class_cpp_header preamble.
struct_enum_register = Template(
    "${generator_pre_code}"
    "typedef ${class_cpp_name} ${class_py_name};\n"
    "void register_${class_py_name}_class(py::module &m){\n"
    '    py::class_<${class_py_name}> myclass(m, "${class_py_name}");\n'
    '    py::enum_<${class_py_name}::${enum_name}>(myclass, "${enum_name}")\n'
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
    "module_exception_translator": module_exception_translator,
    "module_exception_catch": module_exception_catch,
    "header_collection_hpp": header_collection_hpp,
    "class_hpp": class_hpp,
    "class_hpp_register_declaration": class_hpp_register_declaration,
    "class_cpp_header": class_cpp_header,
    "class_cpp_register": class_cpp_register,
    "struct_enum_register": struct_enum_register,
    "free_function": free_function,
    "class_method": class_method,
    "class_constructor": class_constructor,
    "class_virtual_override_header": class_virtual_override_header,
    "smart_pointer_holder": smart_pointer_holder,
    "method_virtual_override": method_virtual_override,
}
