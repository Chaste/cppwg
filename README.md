# cppwg

Automatically generate PyBind11 code for Python wrapping C++ projects.

## Example

There is a full example project with most features you need to get started in `cppwg/test/`. 

Starting with a free function in `simple_function.hpp`:
```c++
#ifndef _SIMPLE_FUNCTION_HPP
#define _SIMPLE_FUNCTION_HPP

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

#endif  // _SIMPLE_FUNCITON_HPP
```

and a package description in `package_info.yaml`:

```yaml
name: py_example

modules:
- name: functions
  free_functions: cppwg_ALL
```

The generator will automatically make the following PyBind wrapper code in `functions.main.cpp`:
```c++
#include <pybind11/pybind11.h>
#include "wrapper_header_collection.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_py_example_functions, m)
{
    m.def("add", &add, "");
}
```

which can be built into a Python module and used as follows:
```python
import _py_example_functions
a = 4
b = 5
c = _py_example_functions.add(4, 5)
print c
>>> 9
```

## Usage
* It is recommended that you [learn how to use PyBind11 first](https://pybind11.readthedocs.io/en/stable/). This project just
generates PyBind11 wrapper code, saving lots of boilerplate in bigger projects.

### Dependencies
* Download the `CastXML` binary (available on [Linux](https://midas3.kitware.com/midas/folder/13152), 
[MacOS](https://midas3.kitware.com/midas/folder/13152), [Windows](https://midas3.kitware.com/midas/folder/13152) )
* Install `pygccxml` with `pip install pygccxml`
* Clone `cppwg` with `git clone https://github.com/jmsgrogan/cppwg.git`

### Test The Installation
* From the directory containing `cppwg` do: `python cppwg/test/wrap_simple_function/generate.py` to generate the PyBind11 wrapper code in `cppwg/test/wrap_simple_function/functions`. To build the wrapper do `cd cppwg/test/; make`. To test the resulting Python package do:
`python example_project/test/test_functions.py`

### Starting a New Project
* Make a wrapper directory in your source tree `mkdir $WRAPPER_DIR`
* Copy the template in `cppwg\test\example_project\generate.py` to a suitable location in your source tree and fill it in.
* Copy the template in `cppwg\test\example_project\package_info.yaml` to a suitable location in your source tree and fill it in.
* Do `python generate.py` to generate the PyBind11 wrapper code in `$WRAPPER_DIR`.
* Follow the [PyBind11 guide](https://pybind11.readthedocs.io/en/stable/compiling.html) for building with CMake.
