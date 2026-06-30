![unit](https://github.com/Chaste/cppwg/actions/workflows/test-unit.yml/badge.svg?branch=develop)
![pip](https://github.com/Chaste/cppwg/actions/workflows/test-shapes-pip.yml/badge.svg?branch=develop)
![ubuntu](https://github.com/Chaste/cppwg/actions/workflows/test-cells-ubuntu.yml/badge.svg?branch=develop)
![conda](https://github.com/Chaste/cppwg/actions/workflows/test-cells-conda.yml/badge.svg?branch=develop)

# cppwg

Automatically generate pybind11 Python wrapper code for C++ projects.

## Installation

Install CastXML (required) and Clang (recommended). On Ubuntu, this would be:

```bash
sudo apt-get install castxml clang
```

Clone the repository and install cppwg:

```bash
git clone https://github.com/Chaste/cppwg.git
cd cppwg
pip install .
```

## Usage

```
usage: cppwg [-h] [-w WRAPPER_ROOT] [-p PACKAGE_INFO] [-c CASTXML_BINARY]
             [-m CASTXML_COMPILER] [--std STD] [--castxml_cflags CASTXML_CFLAGS]
             [-i [INCLUDES ...]] [-q] [-l [LOGFILE]] [-v] SOURCE_ROOT

Generate Python Wrappers for C++ code

positional arguments:
  SOURCE_ROOT           Path to the root directory of the input C++ source code.

options:
  -h, --help            show this help message and exit
  -w, --wrapper_root WRAPPER_ROOT
                        Path to the output directory for the Pybind11 wrapper code.
  -p, --package_info PACKAGE_INFO
                        Path to the package info file.
  -c, --castxml_binary CASTXML_BINARY
                        Path to the castxml executable.
  -m, --castxml_compiler CASTXML_COMPILER
                        Path to a compiler to be used by castxml.
  --std STD             C++ standard e.g. c++17.
  --castxml_cflags CASTXML_CFLAGS
                        Additional flags for the castxml clang frontend. Pass
                        values starting with "-" using "=" e.g.
                        --castxml_cflags="-Wno-deprecated".
  -i, --includes [INCLUDES ...]
                        List of paths to include directories.
  --overwrite           Force rewrite of all wrapper files, even if unchanged.
  -q, --quiet           Disable informational messages.
  -l, --logfile [LOGFILE]
                        Output log messages to a file.
  -v, --version         Print cppwg version.
```

## Example

The project in `examples/shapes` demonstrates `cppwg` usage. We can walk through
the process with the `Rectangle` class in `examples/shapes/src/cpp/primitives`

**Rectangle.hpp**

```cpp
class Rectangle : public Shape<2>
{
public:
  Rectangle(double width=2.0, double height=1.0);
  ~Rectangle();
  //...
};
```

Cppwg needs a configuration file that has a list of classes to wrap and
describes the structure of the Python package to be created.

There is an example configuration file in
`examples/shapes/wrapper/package_info.yaml`.

The extract below from the example configuration file describes a Python package
named `pyshapes` which has a `primitives` module that includes the `Rectangle`
class.

```yaml
name: pyshapes
modules:
  - name: primitives
    classes:
      - name: Rectangle
```

See `package_info.yaml` for more configuration options.

To generate the wrappers:

```bash
cd examples/shapes
cppwg src/cpp \
  --wrapper_root wrapper \
  --package_info wrapper/package_info.yaml \
  --includes src/cpp/geometry src/cpp/math_funcs src/cpp/primitives \
  --std c++17
```

For the `Rectangle` class, this creates two files in
`examples/shapes/wrapper/primitives`.

**Rectangle.cppwg.hpp**

```cpp
void register_Rectangle_class(pybind11::module &m);
```

**Rectangle.cppwg.cpp**

```cpp
namespace py = pybind11;
void register_Rectangle_class(py::module &m)
{
  py::class_<Rectangle, Shape<2> >(m, "Rectangle")
    .def(py::init<double, double>(), py::arg("width")=2, py::arg("height")=1)
    //...
   ;
}
```

The wrapper for `Rectangle` is registered in the `primitives` module.

**primitives.main.cpp**

```cpp
PYBIND11_MODULE(_pyshapes_primitives, m)
{
  register_Rectangle_class(m);
  //...
}
```

To compile the wrappers into a Python package:

```bash
mkdir build && cd build
cmake ..
make
```

The compiled wrapper code can now be imported in Python:

```python
from pyshapes import Rectangle
r = Rectangle(4, 5)
```

## Tips

- Use `examples/shapes` or `examples/cells` as a starting point.
- By default, cppwg only rewrites wrapper files whose content has changed, leaving
  unchanged files untouched so build systems skip recompiling them. Pass
  `--overwrite` to force a full rewrite of all wrapper files.
- To pass extra flags to the castxml clang frontend (e.g. to silence a
  diagnostic), use `--castxml_cflags`. Values starting with `-` must use `=`,
  e.g. `--castxml_cflags="-Wno-deprecated"`.
- To stop C++ exceptions from crashing the Python interpreter, list their class
  names under `exceptions` in the config. cppwg generates a pybind11 exception
  translator for each. By default the message is read with `what()`; set
  `message_method` on an entry to use a different accessor (e.g. `GetMessage`).
  See `examples/shapes/wrapper/package_info.yaml` for an example.
- This only applies to thrown C++ exceptions. Errors from C dependencies that
  use return codes (e.g. a PETSc `PetscErrorCode`) are not caught unless the
  wrapped C++ code converts them into a C++ exception first (for PETSc, via
  `PetscCallThrow()` in a C++-exception build, or by checking the code and
  throwing). See `PetscUtils::ThrowPetscError` in the cells example.
- To let a wrapped class inherit from a base class that is wrapped in a
  different module (either in another package, or another module of this
  package), list the Python modules that register those base classes under
  `imports` on the module that contains the derived class:

  ```yaml
  modules:
    - name: primitives
      # ... defines a base class, e.g. Rectangle
    - name: composites
      imports:
        - pyshapes.primitives._pyshapes_primitives
      classes:
        - name: Square  # inherits Rectangle, which is wrapped in `primitives`
  ```

  cppwg then references such external base classes by their C++ type in the
  `py::class_<...>` definition and imports the listed modules at the start of
  the generated module, so the base types are registered before use. Do not list
  a module in its own `imports` (that would be a circular import). See the
  [pybind11 docs on partitioning code over multiple extension modules](https://pybind11.readthedocs.io/en/stable/advanced/misc.html#partitioning-code-over-multiple-extension-modules).
- See the [pybind11 documentation](https://pybind11.readthedocs.io/) for help on pybind11
  wrapper code.
