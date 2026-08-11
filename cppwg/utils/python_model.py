"""Build a JSON-serialisable model of the Python package layer.

cppwg generates the C++/pybind11 wrappers; a separate step (see
``tools/cppwg_initgen.py``) generates the Python package layer - the
``_generated.py`` files that import each compiled extension and define the
``TemplateClass`` subscript stubs. That step needs, per module, the compiled
module name, the wrapped classes with their template instantiations, and the
enum / free-function names. All of this is on the finalized ``PackageInfo`` tree
but not in a form a standalone script can consume, so ``build_python_model``
distils it into a plain dict that cppwg writes out as ``cppwg_model.yaml``.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cppwg.info.package_info import PackageInfo


def compiled_module_name(package_name: str, module_name: str) -> str:
    """
    Return the pybind11 module name for a package/module, e.g. ``_pyshapes_geometry``.

    Mirrors CppModuleWrapperWriter.full_module_name so the model and the C++
    wrappers agree on the compiled extension name.
    """
    return f"_{package_name}_{module_name}"


def build_python_model(package_info: "PackageInfo") -> dict[str, Any]:
    """
    Distil a PackageInfo tree into a JSON-serialisable Python-package model.

    Parameters
    ----------
    package_info : PackageInfo
        The finalized package info (after wrappers are written, so py_names and
        template_arg_lists are complete).

    Returns
    -------
    dict[str, Any]
        ``{"package": name, "modules": [{"name", "compiled_module", "imports",
        "classes": [{"base", "templated", "instantiations": [{"args", "py_name"}]}],
        "enums": [...], "free_functions": [...]}]}``. Excluded entities are
        omitted (they are not wrapped). An untemplated class has ``templated:
        false`` and a single instantiation with empty ``args``.
    """
    modules = []
    for module in package_info.module_collection:
        classes = []
        for class_info in module.class_collection:
            if class_info.excluded:
                continue

            if class_info.template_arg_lists:
                instantiations = [
                    {"args": [str(arg) for arg in args], "py_name": py_name}
                    for args, py_name in zip(
                        class_info.template_arg_lists, class_info.py_names
                    )
                ]
                templated = True
            else:
                instantiations = [
                    {"args": [], "py_name": py_name} for py_name in class_info.py_names
                ]
                templated = False

            if not instantiations:
                # A class whose every instantiation was pruned contributes nothing.
                continue

            classes.append(
                {
                    "base": class_info.py_name_base(),
                    "templated": templated,
                    "instantiations": instantiations,
                }
            )

        enums = [
            enum_info.name_override or enum_info.name
            for enum_info in module.enum_collection
            if not enum_info.excluded
        ]
        free_functions = [
            free_function_info.name
            for free_function_info in module.free_function_collection
            if not free_function_info.excluded
        ]

        modules.append(
            {
                "name": module.name,
                "compiled_module": compiled_module_name(
                    package_info.name, module.name
                ),
                "imports": list(module.imports),
                "classes": classes,
                "enums": enums,
                "free_functions": free_functions,
            }
        )

    return {"package": package_info.name, "modules": modules}
