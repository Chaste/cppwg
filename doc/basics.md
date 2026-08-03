# Basics

CppWG is driven by a YAML configuration file that describes a **package** made
of one or more **modules**, and the **classes**, **free functions** and
**enums** each module wraps.

```yaml
name: pyshapes                 # package
modules:
  - name: primitives           # module -> _pyshapes_primitives extension
    source_locations:
      - src/cpp/primitives
    classes:
      - name: Rectangle        # class
        excluded_methods:
          - GetArea
```

:::{note}
Each module is compiled into its own extension.
:::

## Selecting what to wrap

As in the example above, you can list classes, free functions and enums
explicitly under a module. Alternatively, you can wrap everything found in the
module's `source_locations` with the `CPPWG_ALL` setting.

```yaml
modules:
  - name: all
    source_locations:
      - src/cpp
    classes: CPPWG_ALL
    free_functions: CPPWG_ALL
    enums: CPPWG_ALL
```

`CPPWG_ALL` must be the **whole** value. A list that merely contains it (e.g.
`[CPPWG_ALL, Foo]`) is treated as literal class names, not "wrap everything".

## Excluding members

Several options drop members that should not (or cannot) be wrapped.

- `excluded: True`: drop the whole class.
- `excluded_methods`: drop methods by name.
- `return_type_excludes`: drop methods whose return type match.
- `arg_type_excludes`: drop methods (and constructors) with an argument type match.
- `constructor_arg_type_excludes`: drop constructors with an argument type match.
- `constructor_signature_excludes`: drop a constructor by its full argument type
  list.

```yaml
modules:
  - name: primitives
    classes:
      - name: Rectangle
        excluded_methods:
          - GetArea                     # drop Rectangle::GetArea
        return_type_excludes:
          - Shape<2>                    # drop methods returning Shape<2>
        arg_type_excludes:
          - AbstractMesh                # drop methods/constructors taking an AbstractMesh
        constructor_arg_type_excludes:
          - AbstractMesh                # drop constructors taking an AbstractMesh
        constructor_signature_excludes:
          - [unsigned]                  # drop the Rectangle(unsigned) constructor
          - [double, double]            # drop the Rectangle(double, double) constructor
      - name: Circle
        excluded: True                  # drop the whole Circle class
```

:::{seealso}
See [Reference](reference.md) for a list of all configuration options.
:::