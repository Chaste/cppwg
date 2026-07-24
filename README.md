[![docs](https://github.com/Chaste/cppwg/actions/workflows/docs.yml/badge.svg?branch=develop)](https://chaste.github.io/cppwg/)
![unit](https://github.com/Chaste/cppwg/actions/workflows/test-unit.yml/badge.svg?branch=develop)
![pip](https://github.com/Chaste/cppwg/actions/workflows/test-shapes-pip.yml/badge.svg?branch=develop)
![ubuntu](https://github.com/Chaste/cppwg/actions/workflows/test-cells-ubuntu.yml/badge.svg?branch=develop)
![conda](https://github.com/Chaste/cppwg/actions/workflows/test-cells-conda.yml/badge.svg?branch=develop)

# CPPWG

Automatically generate [pybind11](https://pybind11.readthedocs.io/) Python
wrapper code for C++ projects.

cppwg reads your C++ source together with a YAML configuration file and emits the
pybind11 registration code for the classes, free functions, and template
instantiations you select — so you describe *what* to expose in config rather
than hand-writing wrapper code.

## Documentation

Full documentation is at **https://chaste.github.io/cppwg/**:

- [Getting started](https://chaste.github.io/cppwg/getting-started.html) — install, run, and a worked example.
- [Configuration reference](https://chaste.github.io/cppwg/configuration.html) — every config option, with types and defaults.
- [Custom generators](https://chaste.github.io/cppwg/custom-generators.html) — inject hand-written binding code.
- [Tips & recipes](https://chaste.github.io/cppwg/tips.html).

## Installation

Install CastXML (required) and Clang (recommended). On Ubuntu:

```bash
sudo apt-get install castxml clang
```

Clone the repository and install cppwg:

```bash
git clone https://github.com/Chaste/cppwg.git
cd cppwg
pip install .
```

## Quick start

Describe the package to generate in a YAML config:

```yaml
name: pyshapes
modules:
  - name: primitives
    classes:
      - name: Rectangle
```

Generate the wrappers:

```bash
cd examples/shapes
cppwg src/cpp \
  --wrapper_root wrapper \
  --package_info wrapper/package_info.yaml \
  --includes src/cpp/geometry src/cpp/math_funcs src/cpp/primitives \
  --std c++17
```

Then compile them into a Python package and import it:

```python
from pyshapes import Rectangle
r = Rectangle(4, 5)
```

See the [full walkthrough](https://chaste.github.io/cppwg/getting-started.html)
and the runnable `examples/shapes` and `examples/cells` projects for the
complete picture.

## Building the docs locally

```bash
pip install ".[docs]"
sphinx-build -b html doc doc/_build/html
```

For a live-reloading dev server that rebuilds on save (and refreshes the
browser), run:

```bash
make -C doc livehtml
```

This serves the docs at http://127.0.0.1:8000 and watches both `doc/` and the
`cppwg/` package, so editing a page or a docstring rebuilds automatically.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
