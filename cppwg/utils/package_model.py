"""Build a serialisable (plain-dict) model of the Python package layer.

cppwg generates the C++/pybind11 wrappers; a separate step (see
``cppwg genpackage``) generates the Python package layer - the
``_generated.py`` files that import each compiled extension and define the
``TemplateClass`` subscript stubs. That step needs, per module, the compiled
module name, the wrapped classes with their template instantiations, and the
enum / free-function names. All of this is on the finalized ``PackageInfo`` tree
but not in a form a standalone script can consume, so ``build_package_model``
distils it into a plain dict that cppwg writes out as ``cppwg_package_model.json``.
"""

from typing import TYPE_CHECKING, Any

from cppwg.info.exclusions import free_function_is_excluded

if TYPE_CHECKING:
    from cppwg.info.package_info import PackageInfo


def compiled_module_name(package_name: str, module_name: str) -> str:
    """
    Return the pybind11 module name for a package/module, e.g. ``_pyshapes_geometry``.

    Mirrors CppModuleWrapperWriter.full_module_name so the model and the C++
    wrappers agree on the compiled extension name.
    """
    return f"_{package_name}_{module_name}"


def build_package_model(package_info: "PackageInfo") -> dict[str, Any]:
    """
    Distil a PackageInfo tree into a serialisable (plain-dict) Python-package model.

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
        "enums": [...], "enum_exports": {enum: [enumerator, ...]},
        "free_functions": [...]}]}``. ``enum_exports`` maps each value-exporting
        enum to the enumerators it binds at module scope. Excluded entities are
        omitted (they are not wrapped). An untemplated class has ``templated:
        false`` and a single instantiation with empty ``args``. Every
        instantiation carries ``cpp_name`` (its C++ type name), which differs
        from ``py_name`` when the class has a name_override.
    """
    modules = []
    for module in package_info.module_collection:
        classes = []
        for class_info in module.class_collection:
            if class_info.excluded:
                continue

            if class_info.template_arg_lists:
                # Carry each instantiation's actual C++ type name (cpp_name), which
                # differs from base<args> when the class has a name_override; the
                # package-layer generator keys nested template arguments by it.
                instantiations = [
                    {
                        "args": [str(arg) for arg in args],
                        "cpp_name": cpp_name,
                        "py_name": py_name,
                    }
                    for args, cpp_name, py_name in zip(
                        class_info.template_arg_lists,
                        class_info.cpp_names,
                        class_info.py_names,
                    )
                ]
                templated = True
            else:
                # Carry cpp_name for the untemplated case too, so a renamed
                # untemplated class (name_override) used as a template argument
                # resolves: the model records its C++ name (e.g. OldName) and the
                # package-layer generator maps OldName -> the Python name.
                instantiations = [
                    {"args": [], "cpp_name": cpp_name, "py_name": py_name}
                    for cpp_name, py_name in zip(
                        class_info.cpp_names, class_info.py_names
                    )
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
        # An enum with .export_values() also binds its enumerators at module
        # scope (e.g. ShapeKind exports CIRCLE). A shared-module split imports
        # each name explicitly, so it must also import those enumerators or
        # subpackage.CIRCLE would vanish. Record them per exporting enum.
        enum_exports = {
            (enum_info.name_override or enum_info.name): [
                value[0] for value in enum_info.decls[0].values
            ]
            for enum_info in module.enum_collection
            if not enum_info.excluded
            and enum_info.decls
            and enum_info.should_export_values()
        }
        # Skip config-excluded functions and those the writer drops for an
        # excluded arg/return type (free_function_is_excluded) - a dropped
        # function emits no binding, so it must not be recorded as wrapped.
        free_functions = [
            free_function_info.name
            for free_function_info in module.free_function_collection
            if not free_function_info.excluded
            and not free_function_is_excluded(free_function_info)
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
                "enum_exports": enum_exports,
                "free_functions": free_functions,
            }
        )

    return {"package": package_info.name, "modules": modules}
