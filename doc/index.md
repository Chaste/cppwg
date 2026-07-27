# CppWG

CppWG is a C++ wrapper generator for Python. It reads your C++ source code,
together with a YAML config file, and emits [pybind11](https://pybind11.readthedocs.io/)
wrapper code. Using the YAML config file, you describe what parts of your C++
project to expose to Python rather than writing pybind11 wrappers directly.

```{toctree}
:maxdepth: 2
:caption: Contents

installation
first-steps
configuration
custom-generators
```
