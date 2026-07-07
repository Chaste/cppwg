"""Main pycells module."""

from ._pycells_all import (
    Cell,
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
    "MacroMesh",
    "MeshFactory",
    "Node",
    "PetscUtils",
    "PottsMesh",
    "Scene",
]
