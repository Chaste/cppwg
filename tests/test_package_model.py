"""Unit tests for cppwg.utils.package_model."""

from types import SimpleNamespace

from cppwg.utils.package_model import build_package_model, compiled_module_name


def _class(base, py_names, template_arg_lists=(), cpp_names=None, excluded=False):
    return SimpleNamespace(
        excluded=excluded,
        py_names=list(py_names),
        cpp_names=list(cpp_names if cpp_names is not None else py_names),
        template_arg_lists=[list(a) for a in template_arg_lists],
        py_name_base=lambda base=base: base,
    )


def _enum(name, name_override="", excluded=False, exported_values=None):
    values = list(exported_values or [])
    return SimpleNamespace(
        name=name,
        name_override=name_override,
        excluded=excluded,
        decls=[SimpleNamespace(values=[(v, i) for i, v in enumerate(values)])],
        should_export_values=lambda values=values: bool(values),
    )


def _free_function(name, excluded=False, arg_types=(), return_type="void", excludes=None):
    _ex = excludes or {}
    decl = SimpleNamespace(
        return_type=SimpleNamespace(decl_string=return_type),
        argument_types=[SimpleNamespace(decl_string=a) for a in arg_types],
    )
    return SimpleNamespace(
        name=name,
        excluded=excluded,
        decls=[decl],
        hierarchy_attribute_gather_flat=lambda key: list(_ex.get(key, [])),
    )


def _module(name, classes=(), enums=(), free_functions=(), imports=()):
    return SimpleNamespace(
        name=name,
        imports=list(imports),
        class_collection=list(classes),
        enum_collection=list(enums),
        free_function_collection=list(free_functions),
    )


def _package(name, modules):
    return SimpleNamespace(name=name, module_collection=list(modules))


def test_compiled_module_name():
    assert compiled_module_name("pyshapes", "geometry") == "_pyshapes_geometry"
    assert compiled_module_name("pycells", "all") == "_pycells_all"


def test_build_model_templated_and_untemplated():
    package = _package(
        "pyshapes",
        [
            _module(
                "geometry",
                classes=[
                    _class(
                        "Point",
                        ["Point_2", "Point_3"],
                        [[2], [3]],
                        cpp_names=["Point<2>", "Point<3>"],
                    )
                ],
            ),
            _module(
                "primitives",
                classes=[
                    _class(
                        "Shape",
                        ["Shape_2", "Shape_3"],
                        [[2], [3]],
                        cpp_names=["Shape<2>", "Shape<3>"],
                    ),
                    _class("UnitSquare", ["UnitSquare"]),  # untemplated
                ],
                enums=[_enum("ShapeKind")],
                imports=["pyshapes.geometry._pyshapes_geometry"],
            ),
        ],
    )

    model = build_package_model(package)

    assert model["package"] == "pyshapes"
    geometry, primitives = model["modules"]

    assert geometry["compiled_module"] == "_pyshapes_geometry"
    (point,) = geometry["classes"]
    assert point == {
        "base": "Point",
        "templated": True,
        "instantiations": [
            {"args": ["2"], "cpp_name": "Point<2>", "py_name": "Point_2"},
            {"args": ["3"], "cpp_name": "Point<3>", "py_name": "Point_3"},
        ],
    }

    assert primitives["imports"] == ["pyshapes.geometry._pyshapes_geometry"]
    shape, unit_square = primitives["classes"]
    assert shape["templated"] is True
    assert unit_square == {
        "base": "UnitSquare",
        "templated": False,
        "instantiations": [
            {"args": [], "cpp_name": "UnitSquare", "py_name": "UnitSquare"}
        ],
    }
    assert primitives["enums"] == ["ShapeKind"]


def test_build_model_omits_excluded_and_pruned():
    package = _package(
        "pkg",
        [
            _module(
                "mod",
                classes=[
                    _class("Kept", ["Kept"]),
                    _class("Gone", ["Gone"], excluded=True),  # excluded
                    _class("Pruned", [], [[2]]),  # all instantiations pruned away
                ],
                enums=[_enum("KeptEnum"), _enum("GoneEnum", excluded=True)],
                free_functions=[
                    _free_function("kept_fn"),
                    _free_function("gone_fn", excluded=True),
                ],
            )
        ],
    )

    (module,) = build_package_model(package)["modules"]

    assert [c["base"] for c in module["classes"]] == ["Kept"]
    assert module["enums"] == ["KeptEnum"]
    assert module["free_functions"] == ["kept_fn"]


def test_build_model_multi_arg_and_class_arg_keys():
    """Multi-arg and class-name-arg instantiations stringify each argument."""
    package = _package(
        "pycells",
        [
            _module(
                "all",
                classes=[
                    _class(
                        "MacroMesh",
                        ["MacroMesh_2_2"],
                        [[2, 2]],
                        cpp_names=["MacroMesh<2, 2>"],
                    ),
                    _class(
                        "CellFactory",
                        ["CellFactory_Cell_2"],
                        [["Cell", 2]],
                        cpp_names=["CellFactory<Cell, 2>"],
                    ),
                ],
            )
        ],
    )

    (module,) = build_package_model(package)["modules"]
    macro, factory = module["classes"]
    assert macro["instantiations"] == [
        {"args": ["2", "2"], "cpp_name": "MacroMesh<2, 2>", "py_name": "MacroMesh_2_2"}
    ]
    assert factory["instantiations"] == [
        {
            "args": ["Cell", "2"],
            "cpp_name": "CellFactory<Cell, 2>",
            "py_name": "CellFactory_Cell_2",
        }
    ]


def test_instantiation_carries_cpp_name_for_name_override():
    """cpp_name is the C++ type name (from cpp_names), not the overridden py name."""
    package = _package(
        "pkg",
        [
            _module(
                "mod",
                classes=[
                    _class("NewName", ["NewName_2"], [[2]], cpp_names=["OldName<2>"]),
                ],
            )
        ],
    )

    (module,) = build_package_model(package)["modules"]
    (cls,) = module["classes"]
    assert cls["instantiations"] == [
        {"args": ["2"], "cpp_name": "OldName<2>", "py_name": "NewName_2"}
    ]


def test_untemplated_name_override_carries_cpp_name():
    """A renamed untemplated class records its C++ name, distinct from py_name.

    This lets the package-layer generator resolve the class when it appears as a
    template argument spelled with its C++ name (OldName -> NewName).
    """
    package = _package(
        "pkg",
        [_module("mod", classes=[_class("NewName", ["NewName"], cpp_names=["OldName"])])],
    )
    (module,) = build_package_model(package)["modules"]
    (cls,) = module["classes"]
    assert cls["instantiations"] == [
        {"args": [], "cpp_name": "OldName", "py_name": "NewName"}
    ]


def test_build_model_omits_free_function_excluded_by_type():
    """A free function the writer drops for an excluded arg type is not recorded.

    Its binding is never emitted, so recording it would make a shared-module
    layout import a symbol that does not exist in the compiled extension.
    """
    package = _package(
        "pkg",
        [
            _module(
                "mod",
                free_functions=[
                    _free_function("kept_fn"),
                    _free_function(
                        "shape_fn",
                        arg_types=["::Shape<2> const &"],
                        excludes={"arg_type_excludes": ["Shape"]},
                    ),
                ],
            )
        ],
    )

    (module,) = build_package_model(package)["modules"]
    assert module["free_functions"] == ["kept_fn"]  # shape_fn dropped, not recorded


def test_enum_name_override_used():
    package = _package(
        "pkg", [_module("mod", enums=[_enum("RawName", name_override="PyName")])]
    )
    (module,) = build_package_model(package)["modules"]
    assert module["enums"] == ["PyName"]
    # A non-exporting enum contributes no enum_exports entry.
    assert module["enum_exports"] == {}


def test_enum_exports_records_exported_enumerators():
    """A value-exporting enum records its enumerators, keyed by the enum py-name."""
    package = _package(
        "pkg",
        [
            _module(
                "mod",
                enums=[
                    _enum("ShapeKind", exported_values=["CIRCLE", "SQUARE"]),
                    _enum("Scoped"),  # scoped/non-exporting -> not recorded
                ],
            )
        ],
    )
    (module,) = build_package_model(package)["modules"]
    assert module["enums"] == ["ShapeKind", "Scoped"]
    assert module["enum_exports"] == {"ShapeKind": ["CIRCLE", "SQUARE"]}
