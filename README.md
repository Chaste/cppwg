[![docs](https://github.com/Chaste/cppwg/actions/workflows/docs.yml/badge.svg?branch=develop)](https://chaste.github.io/cppwg/)
![unit](https://github.com/Chaste/cppwg/actions/workflows/test-unit.yml/badge.svg?branch=develop)
![pip](https://github.com/Chaste/cppwg/actions/workflows/test-shapes-pip.yml/badge.svg?branch=develop)
![ubuntu](https://github.com/Chaste/cppwg/actions/workflows/test-cells-ubuntu.yml/badge.svg?branch=develop)
![conda](https://github.com/Chaste/cppwg/actions/workflows/test-cells-conda.yml/badge.svg?branch=develop)

# CppWG

Automatically generate [pybind11](https://pybind11.readthedocs.io/) Python
wrapper code for C++ projects.

cppwg reads your C++ source and emits the pybind11 code for list of classes you
specify in a YAML configuration file.

## Documentation

Full documentation is at **https://chaste.github.io/cppwg/**:

- [Installation](https://chaste.github.io/cppwg/installation.html) — dependencies and installation steps.
- [First steps](https://chaste.github.io/cppwg/first-steps.html) — a simple worked example.
- [Configuration](https://chaste.github.io/cppwg/configuration.html) — how to describe your package in YAML.
- [Custom generators](https://chaste.github.io/cppwg/custom-generators.html) — inject hand-written binding code.

## Installation

cppwg requires Python 3.10+ and CastXML (Clang is recommended alongside it). On
Ubuntu:

```bash
sudo apt-get install castxml clang
```

Clone the repository and install cppwg, along with the runnable examples:

```bash
git clone https://github.com/Chaste/cppwg.git
cd cppwg
pip install .
```

Or install just the tool, without the examples, directly from GitHub:

```bash
pip install git+https://github.com/Chaste/cppwg.git
```

## Quick start

Describe what to wrap in a YAML config — a package with named modules, each
listing the classes (and free functions) to expose:

```yaml
name: pyshapes
modules:
  - name: primitives
    classes:
      - name: Rectangle
```

Then run cppwg over your source. For the bundled `examples/shapes` project:

```bash
cd examples/shapes
cppwg src/cpp \
  --wrapper_root wrapper \
  --package_info wrapper/package_info.yaml \
  --includes src/cpp/geometry src/cpp/math_funcs src/cpp/primitives \
  --std c++17
```

Then compile the generated wrappers into a Python package and import it:

```python
from pyshapes import Rectangle
r = Rectangle(4, 5)
```

See the [full walkthrough](https://chaste.github.io/cppwg/)
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
