![build](https://github.com/Chaste/cppwg/actions/workflows/build-and-test.yml/badge.svg)

# cppwg

Automatically generate PyBind11 Python wrapper code for C++ projects.

## Example

`examples/shapes/` is a full example project, demonstrating how to generate a Python package `pyshapes` from 
C++ source code. It is recommended that you use it as a template project when getting started.

As a small example, we can start with a free function in `examples/shapes/src/math_funcs/SimpleMathFunctions.hpp`:
```c++
#ifndef _SIMPLEMATHFUNCTIONS_HPP
#define _SIMPLEMATHFUNCTIONS_HPP

/**
 * Add the two input numbers and return the result
 * @param i the first number
 * @param j the second number
 * @return the sum of the numbers
 */
int add(int i, int j)
{
    return i + j;
}

#endif  // _SIMPLEMATHFUNCTIONS_HPP
```

add a package description to `examples/shapes/wrapper/package_info.yaml`:

```yaml
name: pyshapes
modules:
- name: math_funcs
  free_functions: cppwg_ALL
```

and do `python examples/shapes/wrapper/generate.py` (with some suitable arguments).

The generator will make the following PyBind11 wrapper code in `examples/shapes/wrapper/math_funcs/math_funcs.main.cpp`:
```c++
#include <pybind11/pybind11.h>
#include "wrapper_header_collection.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_pyshapes_math_funcs, m)
{
    m.def("add", &add, "");
}
```

which can be built into a Python module and (with some import tidying) used as follows:
```python
from pyshapes import math_funcs
a = 4
b = 5
c = math_funcs.add(4, 5)
print c
>>> 9
```

## Usage
It is recommended that you [learn how to use PyBind11 first](https://pybind11.readthedocs.io/en/stable/). This project 
generates PyBind11 wrapper code, saving lots of boilerplate in bigger projects.

### Dependencies
Developed on the [latest Ubuntu LTS](https://ubuntu.com/about/release-cycle)
version and tested with [supported versions of Python 3](https://devguide.python.org/versions/).

The main dependencies are [pyyaml](https://github.com/yaml/pyyaml), 
[pygccxml](https://github.com/CastXML/pygccxml), and [castxml](https://github.com/CastXML/CastXML), 
which will be automatically pip-installed along with cppwg. Alternatively, 
they can be installed directly with:
 
 ```bash
 pip install pyyaml pygccxml castxml
 ```

### Test the Installation
First, clone the repository with:

```bash
git clone https://github.com/Chaste/cppwg.git
```

Install cppwg by doing:

```bash
cd cppwg
pip install .
```

To generate the full `pyshapes` wrapper, do:

```bash
cd examples/shapes
cppwg src/ \
  --includes src/geometry/ src/math_funcs/ src/primitives/ src/python/ \
  --wrapper_root wrapper/ \
  --package_info wrapper/package_info.yaml
```

To build the example package do:

```bash
mkdir build
cd build
cmake ..
make
```

To test the resulting package do:

```bash
python test_functions.py 
python test_classes.py 
```

### Starting a New Project
* Make a wrapper directory in your source tree e.g. `mkdir wrappers`
* Copy the template in `examples/shapes/wrapper/generate.py` to the wrapper directory and fill it in.
* Copy the template in `examples/shapes/wrapper/package_info.yaml` to the wrapper directory and fill it in.
* Do `python wrappers/generate.py` to generate the PyBind11 wrapper code in the wrapper directory.
* Follow the [PyBind11 guide](https://pybind11.readthedocs.io/en/stable/compiling.html) for building with CMake, using `examples/shapes/CMakeLists.txt` as an initial guide.
