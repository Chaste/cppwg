# First steps

## Shapes example

:::{note}
See [Installation](installation.md) for how to obtain the examples.
:::

Let us walk through `examples/shapes`, which contains a `Rectangle` class we want
to wrap.

**Rectangle.hpp**

`examples/shapes/src/cpp/primitives/Rectangle.hpp`

```cpp
class Rectangle : public Shape<2>
{
public:
  Rectangle(double width=2.0, double height=1.0);
  ~Rectangle();
  //...
};
```

We start by writing a YAML configuration file that lists the classes to wrap.

**package_info.yaml**

`examples/shapes/wrapper/package_info.yaml`

```yaml
name: pyshapes
modules:
  - name: primitives
    classes:
      - name: Rectangle
```

This configuration describes the structure of the Python package we want to
create: a package named `pyshapes` with a `primitives` module that includes the
`Rectangle` class.

:::{note}
See [Configuration reference](configuration.md) for the full list of configuration options.
:::

To generate the wrappers for this example, run:

```bash
cd examples/shapes
cppwg src/cpp \
  --wrapper_root wrapper \
  --package_info wrapper/package_info.yaml \
  --includes src/cpp/geometry src/cpp/math_funcs src/cpp/primitives \
  --std c++17
```

This directs cppwg to:
- Read the C++ source from `src/cpp`.
- Write the generated wrappers to the `wrapper` directory.
- Use the YAML configuration at `wrapper/package_info.yaml`.
- Search the listed directories for header includes.
- Parse the source against the C++17 standard.

:::{note}
See [Command-line usage](#command-line-usage) for other command-line options.
:::

This creates a directory for the `primitives` module at `wrapper/primitives`,
containing the pybind11 wrapper for `Rectangle` as a `.hpp` and `.cpp` file:

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

The directory also contains a wrapper for the `primitives` module itself, in
which the `Rectangle` wrapper is registered:

**primitives.main.cpp**

```cpp
PYBIND11_MODULE(_pyshapes_primitives, m)
{
  register_Rectangle_class(m);
  //...
}
```

To compile the example wrappers, run:

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

:::{note}
See the rest of `examples/shapes` for the full set of generated wrappers.
See also `examples/cells` for a more complex project.
:::

## Command-line usage

```text
usage: cppwg [-h] [-w WRAPPER_ROOT] [-p PACKAGE_INFO] [-c CASTXML_BINARY]
             [-m CASTXML_COMPILER] [--std STD] [--castxml_cflags CASTXML_CFLAGS]
             [-i [INCLUDES ...]] [--overwrite] [-q] [-l [LOGFILE]] [-v] SOURCE_ROOT

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

## Tips

- **Examples.** Use `examples/shapes` or `examples/cells` as a starting point for
  your own project.

- **CastXML flags.** To pass extra flags to the castxml clang frontend (e.g. to
  silence a diagnostic), use `--castxml_cflags`. Values starting with `-` must
  use `=`, e.g. `--castxml_cflags="-Wno-deprecated"`.

- **Pybind11 docs.** See the [pybind11 documentation](https://pybind11.readthedocs.io/)
  for help understanding the generated wrapper code.
