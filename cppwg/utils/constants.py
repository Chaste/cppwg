"""Constants for the cppwg package."""

CPPWG_SOURCEROOT_STRING = "CPPWG_SOURCEROOT"
CPPWG_ALL_STRING = "CPPWG_ALL"

CPPWG_EXT = "cppwg"
CPPWG_HEADER_COLLECTION_FILENAME = f"wrapper_header_collection.{CPPWG_EXT}.hpp"

# Default log file name used when --logfile is passed without a value.
CPPWG_DEFAULT_LOGFILE = f"{CPPWG_EXT}.log"

# The Python-package model cppwg writes into the wrapper root, describing the
# generated modules/classes so a separate step can build the Python package
# layer (see cppwg.utils.python_model and tools/cppwg_initgen.py).
CPPWG_PYTHON_MODEL_FILENAME = "cppwg_model.yaml"

CPPWG_TRUE_STRINGS = ["ON", "YES", "Y", "TRUE", "T", "1"]
CPPWG_FALSE_STRINGS = ["OFF", "NO", "N", "FALSE", "F", "0", ""]

CPPWG_DEFAULT_WRAPPER_DIR = "cppwg_wrappers"

CPPWG_CLASS_OVERRIDE_SUFFIX = "_Overrides"
