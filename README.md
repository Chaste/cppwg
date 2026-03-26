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
             [-m CASTXML_COMPILER] [--std STD] [-i [INCLUDES ...]] [-q] 
             [-l [LOGFILE]] [-v] SOURCE_ROOT

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
  -i, --includes [INCLUDES ...]
                        List of paths to include directories.
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
- See the [pybind11 documentation](https://pybind11.readthedocs.io/) for help on pybind11
  wrapper code.
