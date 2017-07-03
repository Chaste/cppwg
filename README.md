# cppwg
An automatic wrapper generator for C++ projects based on source tree analysis. At the moment it generates wrapper code for the PyBind11 Python wrapper. 

## This software is not ready for use yet. 


## Example

This is a simple test case based on the PyBind11 docs.

Starting with a free function:
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

and a simple project description:

```yaml
name: py_example_project

modules:
- name: functions
  free_functions: cppwg_ALL
```

The generator will automatically make the following PyBind wrapper code:
```c++
#include <pybind11/pybind11.h>
#include "wrapper_header_collection.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_py_example_project_functions, m)
{
    m.def("add", &add, "");
}
```

which can be built into a Python module and used as follows:
```python
a = 4
b = 5
c = py_example_project.functions.add(4, 5)
print c
>>> 9
```

## Usage
* Download the CastXML binary (available on Linux, MacOS, Windows)
* Install pygccxml `pip install pygccxml`
* Make a wrapper directory in your source tree `mkdir $WRAPPER_DIR`
* Download a copy of `cppwg`
* Fill in the template in `test\example_project\generate.py`
* Fill in the template in `test\example_project\package_info.yaml`
* Do `python test\example_project\generate.py`
* Fill in the template in `test\example_project\CMakeLists.txt`
* Build your Python package using `make` or similar.

