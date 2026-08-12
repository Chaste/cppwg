"""Constants for the cppwg package."""

CPPWG_SOURCEROOT_STRING = "CPPWG_SOURCEROOT"
CPPWG_ALL_STRING = "CPPWG_ALL"

CPPWG_EXT = "cppwg"
CPPWG_HEADER_COLLECTION_FILENAME = f"wrapper_header_collection.{CPPWG_EXT}.hpp"

# Default log file name used when --logfile is passed without a value.
CPPWG_DEFAULT_LOGFILE = f"{CPPWG_EXT}.log"

# The package model cppwg writes into the wrapper root, describing the generated
# modules/classes so a separate step can build the Python package layer (see
# cppwg.utils.package_model and tools/cppwg_genpackage.py).
CPPWG_PACKAGE_MODEL_FILENAME = "cppwg_package_model.yaml"

CPPWG_TRUE_STRINGS = ["ON", "YES", "Y", "TRUE", "T", "1"]
CPPWG_FALSE_STRINGS = ["OFF", "NO", "N", "FALSE", "F", "0", ""]

CPPWG_DEFAULT_WRAPPER_DIR = "cppwg_wrappers"

CPPWG_CLASS_OVERRIDE_SUFFIX = "_Overrides"

# Separator inserted between a templated class's base name and its template
# arguments, between successive arguments, and within a nested template argument
# when building the class's Python name (e.g. Foo<2, 2> -> "Foo_2_2",
# MeshFactory<PottsMesh<2>> -> "MeshFactory_PottsMesh_2"). A project can widen
# this (e.g. "__") to avoid Python-name clashes with similarly-named types.
CPPWG_TEMPLATE_ARG_SEPARATOR = "_"
