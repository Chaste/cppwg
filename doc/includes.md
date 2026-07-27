# Includes

Each wrapper needs headers for the types used in its signatures. These usually
come in transitively through the class's own header e.g. the wrapper `Foo.cppwg.cpp`
includes `Foo.hpp`, which normally includes all the types `Foo` uses. When it does
not, the mechanisms below can be used to add the missing headers.

## `source_includes`

Add headers verbatim to a wrapper's `#include` block. This is the manual fallback
for headers the automatic mechanisms below cannot resolve.

```yaml
modules:
  - name: mesh
    classes:
      - name: MeshFactory
        source_includes:
          - PottsMesh.hpp    # emitted as #include "PottsMesh.hpp"
          - <vector>         # emitted as #include <vector>
```

:::{note}
A bare `Foo.hpp` is quoted, and an angle-bracket `<foo>` is emitted as-is.
:::

## `auto_includes`

With `auto_includes: True`, cppwg scans each wrapper for the types it uses, in
method and constructor signatures, and in template-instantiation arguments. It
adds the header for every **project type** it finds. Library types (`std::`,
boost, PETSc, VTK, etc.) are left alone.

```yaml
modules:
  - name: mesh
    classes:
      - name: MeshFactory
        auto_includes: True   # resolves PottsMesh.hpp from the signature
```

:::{note}
- `auto_includes` is off by default and inherits to lower levels.
- It skips a type whose name is defined in more than one header.
- It does nothing when `common_include_file` is enabled.
:::

## `typecasters`

A wrapped signature may expose a type pybind11 cannot convert on its own (e.g. a
PETSc `Vec` or `Mat`). This needs a **type-caster header**: a C++ shim that
teaches pybind11 how to translate a C++ type to and from a Python object.

:::{note}
cppwg does not generate type casters. You supply the header and cppwg adds it to
the wrappers that need it. See the
[pybind11 docs](https://pybind11.readthedocs.io/en/stable/advanced/cast/custom.html)
for how to write custom type casters.
:::

List your casters under `typecasters`, each with the `header` and the `types` it
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

cppwg adds each caster's header only to the wrappers whose signatures use one of
its `types`. Alternatively, you can add the headers manually to each class with
`source_includes`.

:::{seealso}
See [Reference](reference.md) for a list of all configuration options.
:::
