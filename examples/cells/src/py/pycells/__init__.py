"""Main pycells module.

The compiled-extension imports and TemplateClass subscript stubs are generated
by tools/cppwg_genpackage.py into _generated.py; add any hand-written code here.
Curation rationale (why Facet<1>/Corner<1>/AbstractMesh are or aren't wrapped)
lives with the C++ sources and examples/cells/dynamic/config.yaml.
"""

from ._generated import *  # noqa: F401,F403
