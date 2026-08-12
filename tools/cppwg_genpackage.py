#!/usr/bin/env python3
"""Standalone launcher for the cppwg package-layer generator.

The implementation lives in :mod:`cppwg.genpackage`; the canonical invocation is
``cppwg genpackage ...``. This launcher lets the generator also be run directly
from a checkout (``python tools/cppwg_genpackage.py ...``) when cppwg is
importable.
"""

import sys

from cppwg.genpackage import main

if __name__ == "__main__":
    sys.exit(main())
