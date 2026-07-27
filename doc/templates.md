# Templates

Each instantiation of a templated class must be wrapped separately. There are
two ways to specify which instantiations to wrap i.e. listing them manually or
discovering them from the source (or a combination of both).

## `template_substitutions`

Manually list instantiations as a `signature` with a list of `replacement`
argument lists:

```yaml
modules:
  - name: mesh
    classes:
      - name: AbstractMesh
        template_substitutions:
          - signature: <unsigned ELEMENT_DIM, unsigned SPACE_DIM>
            replacement: [[2, 2], [3, 3]]
```

The configuration above wraps:

```cpp
AbstractMesh<2, 2>
AbstractMesh<3, 3>
```

:::{note}
Each `replacement` must have one value per template parameter in the `signature`.
:::

## `discover_template_instantiations`

With `discover_template_instantiations: True`, cppwg automatically scans the
`.cpp` source files to find explicit instantiations:

```yaml
discover_template_instantiations: True   # package level: applies to all classes
modules:
  - name: mesh
    classes:
      - name: AbstractMesh
```

Given the explicit instantiations below in the `.cpp` sources, the configuration
above wraps `AbstractMesh<2, 2>` and `AbstractMesh<3, 3>`, the same result as
the `template_substitutions` example above, without listing them by hand:

```cpp
template class AbstractMesh<2, 2>;
template class AbstractMesh<3, 3>;
```

Discovery reads literal `template class` statements directly via text parsing
and falls back to CastXML when all instantiations are macro-generated. A file
that mixes literal and macro-generated instantiations is not fully discovered and
must be configured manually with `template_substitutions`.

:::{caution}
Recovering a **defaulted** trailing template argument (such as
`<unsigned T, unsigned U=T>`) consistently from an explicit instantiation
declared via a macro requires **CastXML >= 0.6.0**. See the `MacroMesh` class in
`examples/cells` for an example.
:::

## `discover_arg_excludes`

To filter out specific instantiations during automatic discovery, map a
template-parameter name to the argument values to drop:

```yaml
discover_arg_excludes:
  DIM: [0]
  ELEMENT_DIM: [0]
  SPACE_DIM: [0]
```

The configuration above drops any discovered instantiation that binds `DIM`,
`ELEMENT_DIM`, or `SPACE_DIM` to `0`, while keeping e.g. `Foo<SPACE_DIM=1>`.

Matching is **by parameter name**, so a `0` bound to a parameter that is not
listed survives. For example, with the signature
`<unsigned SPACE_DIM, unsigned ELEMENT_DIM, unsigned PROBLEM_DIM>`, the
instantiation `Bar<1, 1, 0>` is kept as its trailing `0` is bound to
`PROBLEM_DIM`, which is not in the map. Only discovered instantiations are
filtered; `template_substitutions` are always wrapped as written.

:::{note}
A key may be the bare parameter name (`ELEMENT_DIM`) or carry a leading type
(`unsigned ELEMENT_DIM`).
:::

## Auto-excluded instantiations

cppwg automatically drops a discovered instantiation whose wrapped methods take
or return a template type that is never instantiated. These would otherwise fail
to link or import with an undefined symbol further downstream. See `Corner` and
`Facet` in `examples/cells`.

:::{seealso}
See [Reference](reference.md) for a list of all configuration options.
:::
