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
- A templated class's instantiations share a single wrapper file: `Foo<2>` and
  `Foo<3>` are wrapped in one `Foo.cppwg.hpp` / `Foo.cppwg.cpp` pair (declaring
  and defining a `register_Foo_2_class` and `register_Foo_3_class` each) rather
  than a separate file pair per instantiation. This reduces the number of
  generated files, and the translation units the build has to compile.
- To pass extra flags to the castxml clang frontend (e.g. to silence a
  diagnostic), use `--castxml_cflags`. Values starting with `-` must use `=`,
  e.g. `--castxml_cflags="-Wno-deprecated"`.
- To wrap a templated class for each of its explicit instantiations without
  hand-writing `template_substitutions`, set `discover_template_instantiations`
  (see `examples/shapes/wrapper/package_info.yaml`). cppwg finds the
  instantiations (e.g. `template class Foo<2, 2>;`) in the source `.cpp` files.
  Instantiations declared through a macro are found via CastXML; recovering a
  **defaulted** trailing template argument from such a macro instantiation
  requires **CastXML >= 0.6.0** (older versions drop it, e.g. naming
  `Foo<2, 2>` as `Foo<2>`). See the `MacroMesh` class in `examples/cells`.
  Discovery reads literal `template class` statements directly and only parses a
  `.cpp` with CastXML when *all* of its instantiations are macro-generated. A
  file that **mixes** literal and macro-generated instantiations is not fully
  discovered — its macro-generated ones are missed — so configure those manually
  with `template_substitutions`.
- To stop discovery wrapping instantiations you do not want (e.g. everything the
  source instantiates at a spatial dimension of 1), set `discover_arg_excludes`,
  a map of template parameter name to the argument values to drop:

  ```yaml
  discover_arg_excludes:
    DIM: [1]
    ELEMENT_DIM: [1]
    SPACE_DIM: [1]
  ```

  A discovered instantiation is dropped when the argument bound to a listed
  parameter is one of its values, so `Foo<SPACE_DIM=1>` is dropped but
  `Foo<SPACE_DIM=2>` is kept. Matching is **by parameter name**, so a value that
  is a spatial dimension for one parameter but incidental for another — e.g. a
  trailing `PROBLEM_DIM` of 1 in `Bar<2, 2, 1>` — is only excluded where it is
  actually named. Only discovered instantiations are filtered;
  `template_substitutions` are always wrapped as written. A key may be the bare
  parameter name (`ELEMENT_DIM`) or carry a leading type as a
  `template_substitutions` signature spells it (`unsigned ELEMENT_DIM`). Set it
  at any level (package, module or class); it inherits down to classes.
- cppwg automatically drops a wrapped template instantiation whose wrapped
  interface (a non-excluded method or constructor) takes or returns a **project
  template type that is never instantiated** — which would otherwise fail to
  link or import with an undefined symbol. Each drop is logged, e.g.
  `Excluding Foo<1>: wrapped interface depends on uninstantiated type Bar<0>`.
  This typically happens at a dimensional boundary — a low-dimensional element
  (e.g. `Facet<1>`) whose faces are a never-instantiated `Facet<0>`. To keep
  such a class, instantiate its dependency (see `Corner` in `examples/cells`);
  otherwise the drop leaves the safe instantiations wrapped (see `Facet`).
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
- A wrapped signature may expose a type that pybind11 cannot convert on its own
  (e.g. a PETSc `Vec`, a VTK `vtkSmartPointer<...>`, a boost ublas `c_vector`),
  which needs a **type-caster header** included in the wrapper. Instead of adding
  that header by hand under `source_includes` for every affected class, list your
  casters once under `typecasters`, each with the `header` and the `types` it
  handles:

  ```yaml
  typecasters:
    - header: caster_petsc.h
      types: [Vec, Mat]
    - header: PybindVTKTypeCaster.h
      types: [vtkSmartPointer]
    - header: PybindUblasTypeCaster.hpp
      types: [boost::numeric::ublas::c_vector]
  ```

  cppwg then adds a caster's header to a class's wrapper only when that class's
  wrapped method or constructor signatures actually use one of its `types` — and
  to no other wrapper, keeping these heavy headers out of every wrapper that does
  not need them (they are never added to the shared header collection). Because
  matching is against the type as it appears in the generated signature, spell
  each `type` as it is written there: as a whole token, case-sensitively, and
  namespace-qualified where applicable (`boost::numeric::ublas::c_vector`, not
  `vector`; `Vec` matches `::Vec` but not `c_vector`). You still add the caster
  directories to your build's include paths, exactly as before. Free functions
  are not covered — a free function using a caster type still needs the header
  added manually. See `examples/cells/dynamic/config.yaml`.
- A wrapped signature may use another **project type** whose definition the
  class's own header only forward-declares — e.g. a `MeshFactory<MESH>` whose
  `generateMesh()` returns a `PottsMesh` it never `#include`s. The wrapper then
  needs that type's header (unless you use `common_include_file`, which pulls in
  everything). Rather than listing it by hand under `source_includes`, set
  `auto_includes: True` (at package, module or class level; it inherits down the
  info tree, and is off by default):

  ```yaml
  modules:
    - name: mymod
      classes:
        - name: MeshFactory
          auto_includes: True   # resolves PottsMesh.hpp from the signature
  ```

  cppwg then scans each such class's wrapped method/constructor signatures, and
  for every **project type** it finds (a class defined under the module
  `source_locations`) adds that class's header to the wrapper. Only project types
  are resolved — library types (`std::`, boost, PETSc, VTK, …) are left alone —
  and a type name that is defined in more than one header is treated as ambiguous
  and left for a manual `source_includes`. It is a no-op with
  `common_include_file`, and does not cover types that appear only in
  hand-written `custom_generator` code (cppwg cannot see those) — a generator
  that names such types can add their headers itself by overriding
  `get_source_includes()` (see below). See the `MeshFactory` class in
  `examples/cells/dynamic/config.yaml`.
- A `custom_generator` can emit code that references types cppwg never sees in
  the parsed signatures (e.g. a template-method instantiation like
  `AddCellWriter<CellAgesWriter>` built from a hard-coded list). Those headers
  cannot be auto-included and would otherwise have to be repeated under
  `source_includes`. Instead, override `get_source_includes()` on the generator
  (a subclass of `cppwg.templates.custom.Custom`) to return the header names —
  cppwg adds them to the wrapper's `#include` block (deduplicated, quoted or
  `<...>` form), so the generator and the includes its code needs live in one
  place:

  ```python
  class PopulationWriterCustomTemplate(cppwg.templates.custom.Custom):
      WRITERS = ["CellAgesWriter", "CellIdWriter", ...]

      def get_class_cpp_def_code(self, class_name):
          return "".join(
              f'.def("AddCellWriter{w}", &{class_name}::AddCellWriter<{w}>)\n'
              for w in self.WRITERS
          )

      def get_source_includes(self, *args, **kwargs):
          return [f"{w}.hpp" for w in self.WRITERS]
  ```
- A wrapped class can inherit from a base class wrapped in a **different
  module**, as long as that base is registered somewhere that gets imported
  first. Opt in per module with `imports`, which lists the Python modules to
  import at the start of the generated module (so their base types are
  registered before this module's classes). Do not list a module in its own
  `imports` (that would be a circular import).

  cppwg only emits an external base when it can confirm the base is registered,
  to avoid generating a `py::class_<...>` with an unregistered base (e.g. a
  framework/utility base), which fails at import. There are two cases:

  - **Base wrapped in another module of the same package** — detected
    automatically; just `import` that module:

    ```yaml
    modules:
      - name: primitives        # defines the base class, e.g. Rectangle
      - name: composites
        imports:
          - pyshapes.primitives._pyshapes_primitives
        classes:
          - name: Square        # inherits Rectangle, wrapped in `primitives`
    ```

  - **Base wrapped in another package** (unknown to this cppwg run) — also list
    the base class name under `external_bases` so cppwg knows it is registered
    by an imported module (names match without template arguments, and with or
    without namespace qualification):

    ```yaml
    modules:
      - name: all
        imports:
          - ext_pkg._ext_mod
        external_bases:
          - AbstractFoo       # MyFoo inherits AbstractFoo, wrapped in ext_pkg
        classes:
          - name: MyFoo
    ```

  See the
  [pybind11 docs on partitioning code over multiple extension modules](https://pybind11.readthedocs.io/en/stable/advanced/misc.html#partitioning-code-over-multiple-extension-modules).
- See the [pybind11 documentation](https://pybind11.readthedocs.io/) for help on pybind11
  wrapper code.
