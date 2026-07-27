# Inheritance

Configuration for classes that inherit from one another, whether within a single
module or across module and package boundaries.

## `exclude_inherited_overrides`

Normally, cppwg emits a `.def` binding for every class method, even if it merely
overrides a virtual method already wrapped on a base class. This is redundant:
pybind11 inheritance and C++ virtual dispatch already expose the override to
Python through the base class's binding.

Set `exclude_inherited_overrides: True` to remove these extra `.def` bindings.
This can shrink the size of wrappers in large projects. The [virtual
trampoline](https://pybind11.readthedocs.io/en/stable/advanced/classes.html)
is still generated, so Python subclasses can still override the
method.

```yaml
exclude_inherited_overrides: True   # package level: applies to all classes
modules:
  - name: primitives
    classes:
      - name: Shape        # declares virtual GetArea()
      - name: Rectangle    # overrides GetArea()
```

With the configuration above, `Rectangle`'s wrapper omits the redundant binding:

```cpp
py::class_<Rectangle, Shape>(m, "Rectangle")
  .def(py::init<>())
  // .def("GetArea", ...) is not emitted; Shape's binding already exposes it
  ;
```

:::{note}
An override is only skipped when a wrapped base declares a matching virtual (same
name, argument types, and const-ness). It is kept when another overload of the
same name would otherwise be shadowed. It is also kept when the base class is in
a module not listed in `imports` or when it has been excluded from the base.
:::

## `imports`

A wrapped class can inherit from a base class registered in a different
**module**, as long as that module is imported first. Use `imports` to list the
modules to import at the start of the generated module.

cppwg only emits an external base when it can confirm the base is registered.
This avoids a `py::class_<...>` with an unregistered base, which would fail
further downstream during Python import.

**Base wrapped in another module of the same package**

These are detected automatically when the relevant module is added to `imports`:

```yaml
modules:
  - name: primitives        # defines the base class, e.g. Rectangle
  - name: composites
    imports:
      - pyshapes.primitives._pyshapes_primitives
    classes:
      - name: Square        # inherits Rectangle, wrapped in `primitives`
```

:::{caution}
Listing a module in its own `imports` will cause a circular import.
:::

**Base wrapped in another package**

Add the relevant module to `imports` as above, and also list the base class name
under `external_bases` so cppwg knows it is registered by an imported module:

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

:::{note}
Names in `external_bases` match without template arguments, and with or without
namespace qualification.
:::

:::{seealso}
- See the [pybind11 docs](https://pybind11.readthedocs.io/en/stable/advanced/misc.html#partitioning-code-over-multiple-extension-modules)
on partitioning code over multiple extension modules.
- See [Reference](reference.md) for a list of all configuration options.
:::
