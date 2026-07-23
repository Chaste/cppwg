"""Main pycells module."""

from ._pycells_all import (
    Cell,
    CellFactory_Cell_2,
    CellFactory_Cell_3,
    Corner_2,
    Facet_2,
    MacroMesh_2_2,
    MacroMesh_3_3,
    MeshFactory_PottsMesh_2,
    MeshFactory_PottsMesh_3,
    Node_2,
    Node_3,
    PetscUtils,
    PottsMesh_2,
    PottsMesh_3,
    Scene_2,
    Scene_3,
)
from ._syntax import TemplateClassDict

# CellFactory<CELL_TYPE, DIM> names CELL_TYPE only as a template argument, so
# cppwg's auto_includes resolved Cell.hpp from the instantiation arguments (not
# a signature) - see CellFactory.hpp and examples/cells/dynamic/config.yaml.
CellFactory = TemplateClassDict(
    {
        ("Cell", "2"): CellFactory_Cell_2,
        ("Cell", "3"): CellFactory_Cell_3,
    }
)

# Only Facet<2> is wrapped (curated). Facet<1> is deliberately left unwrapped;
# wrapping it would reference the never-instantiated Facet<0> and fail to import
# (see Facet.hpp and examples/cells/dynamic/config.yaml).
Facet = TemplateClassDict(
    {
        ("2",): Facet_2,
    }
)

# Non-curated counterpart to Facet: discovery finds Corner<1> and Corner<2>, and
# cppwg auto-drops Corner<1> (its GetSub returns the never-instantiated
# Corner<0>), so only Corner<2> is wrapped (see Corner.hpp).
Corner = TemplateClassDict(
    {
        ("2",): Corner_2,
    }
)

MacroMesh = TemplateClassDict(
    {
        ("2", "2"): MacroMesh_2_2,
        ("3", "3"): MacroMesh_3_3,
    }
)

MeshFactory = TemplateClassDict(
    {
        ("PottsMesh", "2"): MeshFactory_PottsMesh_2,
        ("PottsMesh", "3"): MeshFactory_PottsMesh_3,
    }
)

Node = TemplateClassDict(
    {
        ("2",): Node_2,
        ("3",): Node_3,
    }
)

PottsMesh = TemplateClassDict(
    {
        ("2",): PottsMesh_2,
        ("3",): PottsMesh_3,
    }
)

Scene = TemplateClassDict(
    {
        ("2",): Scene_2,
        ("3",): Scene_3,
    }
)

__all__ = [
    "Cell",
    "CellFactory",
    "Corner",
    "Facet",
    "MacroMesh",
    "MeshFactory",
    "Node",
    "PetscUtils",
    "PottsMesh",
    "Scene",
]
