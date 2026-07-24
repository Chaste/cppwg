# Configuration reference

cppwg is driven by a YAML configuration file (passed with `--package_info`). It
describes a **package** made of one or more **modules** (each compiled to its own
extension), and the **classes** and **free functions** each module wraps.

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

## Option inheritance

Options fall into two groups:

- **Level-specific options** are only meaningful at one level (e.g. `modules` at
  the package level, `imports` at the module level, `name_override` at the class
  level).
- **Common options** may be set at the package, module, **or** class level and
  **inherit downwards**: a value set on the package applies to every module and
  class unless a lower level overrides it. This lets you set, say,
  `smart_ptr_type` once for the whole package.

The tables below mark common options accordingly.

## Package options

Set at the top level of the file.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | `cppwg_package` | Package name; prepended to every module's extension name (`_{package}_{module}`). |
| `modules` | list | – | The modules to build. See [Module options](#module-options). |
| `common_include_file` | bool | `True` | If true, every wrapper includes a single shared header collection instead of its own headers. Turn **off** so each wrapper includes only what it needs. |
| `exceptions` | list | `[]` | C++ exception classes to translate into Python. See [Exceptions](#exceptions). |
| `typecasters` | list | `[]` | Type-caster headers to auto-include by type. See [Type casters](#type-casters). |
| `exclude_default_args` | bool | `False` | If true, omit C++ default argument values from the generated bindings. |
| `exclude_inherited_overrides` | bool | `False` | If true, skip redundant `.def`s for methods that only override a virtual already wrapped on a wrapped base. See [Excluding inherited overrides](#excluding-inherited-overrides). |
| `source_hpp_patterns` | list[str] | `["*.hpp"]` | Glob patterns for the header files cppwg scans. |
| `source_cpp_patterns` | list[str] | `["*.cpp"]` | Glob patterns for the source files cppwg scans (used for template-instantiation discovery). |

All [common options](#common-options) may also be set here.

## Module options

Each entry under `modules:`.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | `cppwg_module` | Module name; the extension is `_{package}_{name}`. |
| `source_locations` | list[str] | `[]` | Directories (relative to the source root) whose classes this module wraps. |
| `classes` | list | `[]` | Classes to wrap, or the string `CPPWG_ALL` to wrap every class found. See [Selecting what to wrap](#selecting-what-to-wrap). |
| `free_functions` | list | `[]` | Free functions to wrap, or `CPPWG_ALL`. |
| `imports` | list[str] | `[]` | Python modules to import at the start of this module, so their types are registered first. Required for cross-module inheritance. See [Cross-module inheritance](#cross-module-and-cross-package-inheritance). |
| `external_bases` | list[str] | `[]` | Base-class names registered by an imported **package**, so cppwg will emit them as bases. See [Cross-module inheritance](#cross-module-and-cross-package-inheritance). |

All [common options](#common-options) may also be set here.

## Class options

Each entry under a module's `classes:`.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | – | The C++ class name (required). |
| `name_override` | str | `""` | Python name for the class, if different from the C++ name. |
| `source_file` | str | `""` | Header to attribute the class to, when the class name does not match its file name. |

All [common options](#common-options) may also be set here.

## Common options

Settable at the package, module, or class level; they inherit downwards.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `excluded` | bool | `False` | Exclude the whole class from wrapping. |
| `excluded_methods` | list[str] | `[]` | Method names to skip. |
| `arg_type_excludes` | list[str] | `[]` | Skip any method/constructor with an argument type matching one of these. |
| `return_type_excludes` | list[str] | `[]` | Skip any method with a return type matching one of these. |
| `constructor_arg_type_excludes` | list[str] | `[]` | Skip any constructor with an argument type matching one of these. |
| `constructor_signature_excludes` | list[list[str]] | `[]` | Skip a constructor whose full argument-type list matches an entry. |
| `template_substitutions` | list | `[]` | Explicit template instantiations to wrap. See [Template instantiations](#template-instantiations). |
| `discover_template_instantiations` | bool | `None` | Auto-discover explicit instantiations from the source. See [Template instantiations](#template-instantiations). |
| `discover_arg_excludes` | dict | `{}` | Drop discovered instantiations by template-argument value. See [Template instantiations](#template-instantiations). |
| `auto_includes` | bool | `None` | Auto-resolve headers for project types used in wrapped signatures. See [Includes](#includes). |
| `source_includes` | list[str] | `[]` | Extra headers to add to the wrapper's `#include` block. |
| `smart_ptr_type` | str | `""` | Holder type declared for wrapped classes, e.g. `boost::shared_ptr`. Use one holder consistently across a hierarchy. |
| `pointer_call_policy` | str | `""` | Default pybind11 `return_value_policy` for methods returning a pointer, e.g. `reference`. |
| `reference_call_policy` | str | `""` | Default pybind11 `return_value_policy` for methods returning a reference, e.g. `reference_internal`. |
| `custom_generator` | str | `""` | Path to a Python template that injects extra binding code. See [Custom generators](custom-generators.md). |
| `prefix_text` | str | `""` | Text emitted at the top of each wrapper file (e.g. a licence header). |
| `prefix_code` | list[str] | `[]` | Lines emitted before a class's registration block. |
| `suffix_code` | list[str] | `[]` | Lines emitted after a class's `.def` chain, before the closing `;`. |

`CPPWG_SOURCEROOT` in a path value (e.g. in `custom_generator`) is replaced with
the source root directory.

---

## Selecting what to wrap

List classes and free functions explicitly under a module, or wrap everything
found in the module's `source_locations` with the sentinel string `CPPWG_ALL`:

```yaml
modules:
  - name: all
    source_locations:
      - src/cpp
    classes: CPPWG_ALL
    free_functions: CPPWG_ALL
```

`CPPWG_ALL` must be the **whole** value — a list that merely contains it (e.g.
`[CPPWG_ALL, Foo]`) is treated as literal class names, not "wrap everything".

## Template instantiations

A templated class must be wrapped once per instantiation. There are two ways to
select them; they can be combined.

### Explicit: `template_substitutions`

List each instantiation as a `signature` (the template parameters) and the
`replacement` argument lists:

```yaml
- name: AbstractElement
  template_substitutions:
    - signature: <unsigned ELEMENT_DIM, unsigned SPACE_DIM>
      replacement: [[1, 2], [2, 2], [2, 3], [3, 3]]
```

Each replacement's length must match the parameter count.

### Automatic: `discover_template_instantiations`

Set `discover_template_instantiations: True` to have cppwg find explicit
instantiations (e.g. `template class Foo<2, 2>;`) in the source `.cpp` files,
without hand-writing them. Instantiations declared through a macro are found via
CastXML; recovering a **defaulted** trailing template argument from such a macro
instantiation requires **CastXML >= 0.6.0** (older versions drop it, e.g. naming
`Foo<2, 2>` as `Foo<2>`). See the `MacroMesh` class in `examples/cells`.

Discovery reads literal `template class` statements directly and only parses a
`.cpp` with CastXML when *all* of its instantiations are macro-generated. A file
that **mixes** literal and macro-generated instantiations is not fully
discovered — its macro-generated ones are missed — so configure those manually
with `template_substitutions`.

### Filtering discovery: `discover_arg_excludes`

To stop discovery from wrapping instantiations you do not want (e.g. everything
the source instantiates at a spatial dimension of 1), map a template-parameter
name to the argument values to drop:

```yaml
discover_arg_excludes:
  DIM: [1]
  ELEMENT_DIM: [1]
  SPACE_DIM: [1]
```

A discovered instantiation is dropped when the argument bound to a listed
parameter is one of its values, so `Foo<SPACE_DIM=1>` is dropped but
`Foo<SPACE_DIM=2>` is kept. Matching is **by parameter name**, so a value that is
a spatial dimension for one parameter but incidental for another — e.g. a
trailing `PROBLEM_DIM` of 1 in `Bar<2, 2, 1>` — is only excluded where it is
actually named. Only discovered instantiations are filtered;
`template_substitutions` are always wrapped as written. A key may be the bare
parameter name (`ELEMENT_DIM`) or carry a leading type as a
`template_substitutions` signature spells it (`unsigned ELEMENT_DIM`).

### Uninstantiated-dependency dropping

cppwg automatically drops a wrapped instantiation whose wrapped interface (a
non-excluded method or constructor) takes or returns a **project template type
that is never instantiated** — which would otherwise fail to link or import with
an undefined symbol. Each drop is logged, e.g.
`Excluding Foo<1>: wrapped interface depends on uninstantiated type Bar<0>`. This
typically happens at a dimensional boundary — a low-dimensional element (e.g.
`Facet<1>`) whose faces are a never-instantiated `Facet<0>`. To keep such a
class, instantiate its dependency (see `Corner` in `examples/cells`); otherwise
the drop leaves the safe instantiations wrapped (see `Facet`).

## Excluding members

Several options drop members that cannot or should not be wrapped. Type matches
are on the type as it appears in the C++ signature, as a whole token,
case-sensitively, and namespace-qualified where applicable.

- `excluded: True` — drop the whole class.
- `excluded_methods` — drop methods by name.
- `return_type_excludes` / `arg_type_excludes` — drop methods (and, for args,
  constructors) whose return/argument type matches.
- `constructor_arg_type_excludes` — drop constructors by an argument type (e.g.
  a mesh reference the constructor stores a raw pointer to).
- `constructor_signature_excludes` — drop a constructor by its full argument-type
  list, e.g. `- [unsigned]` to drop a single-`unsigned` constructor.

## Includes

Each non-common wrapper needs the headers for the types in its signatures.
cppwg offers three complementary mechanisms so you rarely list headers by hand.

### `source_includes`

Extra headers added verbatim to the wrapper's `#include` block. A bare name
(`Foo.hpp`) is quoted; an angle-bracket string (`<foo>`) is emitted as-is.

### `auto_includes`

A wrapped signature may use another **project type** whose definition the class's
own header only forward-declares — e.g. a `MeshFactory<MESH>` whose
`generateMesh()` returns a `PottsMesh` it never `#include`s. Set
`auto_includes: True` (at any level; it inherits down and is off by default):

```yaml
modules:
  - name: mymod
    classes:
      - name: MeshFactory
        auto_includes: True   # resolves PottsMesh.hpp from the signature
```

cppwg scans each such class's wrapped method/constructor signatures, plus the
template arguments of its instantiations (e.g. a `Foo<Bar, DIM>` needs `Bar.hpp`
even if `Bar` never appears in a method/constructor signature), and for every
**project type** it finds (a class defined under the module `source_locations`)
adds that class's header. Only project types are resolved — library types
(`std::`, boost, PETSc, VTK, …) are left alone — and a type name defined in more
than one header is treated as ambiguous and left for a manual `source_includes`.
It is a no-op with `common_include_file`, and does not cover types that appear
only in hand-written `custom_generator` code. See the `MeshFactory` class in
`examples/cells/dynamic/config.yaml`.

### Type casters

A wrapped signature may expose a type pybind11 cannot convert on its own (a PETSc
`Vec`, a VTK `vtkSmartPointer<...>`, a boost ublas `c_vector`), which needs a
**type-caster header** in the wrapper. List your casters once under
`typecasters`, each with the `header` and the `types` it handles:

```yaml
typecasters:
  - header: caster_petsc.h
    types: [Vec, Mat]
  - header: PybindVTKTypeCaster.h
    types: [vtkSmartPointer]
  - header: PybindUblasTypeCaster.hpp
    types: [boost::numeric::ublas::c_vector]
```

cppwg adds a caster's header to a wrapper only when that class's wrapped
signatures actually use one of its `types` — and to no other wrapper, keeping
these heavy headers out of wrappers that do not need them (they are never added
to the shared header collection). Because matching is against the type as it
appears in the generated signature, spell each `type` as written there: as a
whole token, case-sensitively, and namespace-qualified (`boost::numeric::ublas::c_vector`,
not `vector`; `Vec` matches `::Vec` but not `c_vector`). You still add the caster
directories to your build's include paths. Free functions are not covered — a
free function using a caster type still needs the header added manually. See
`examples/cells/dynamic/config.yaml`.

A caster converts a type only at the **call boundary** (arguments and returns),
not for a type stored in a container or as object state, and not for non-const
reference (out-)parameters. Signatures using a caster type in one of those shapes
still have to be excluded.

## Cross-module and cross-package inheritance

A wrapped class can inherit from a base wrapped in a **different module**, as long
as that base is registered somewhere imported first. Opt in per module with
`imports`, which lists the Python modules to import at the start of the generated
module. Do not list a module in its own `imports` (a circular import).

cppwg only emits an external base when it can confirm the base is registered, to
avoid a `py::class_<...>` with an unregistered base (which fails at import). Two
cases:

**Base wrapped in another module of the same package** — detected automatically;
just `import` that module:

```yaml
modules:
  - name: primitives        # defines the base class, e.g. Rectangle
  - name: composites
    imports:
      - pyshapes.primitives._pyshapes_primitives
    classes:
      - name: Square        # inherits Rectangle, wrapped in `primitives`
```

**Base wrapped in another package** (unknown to this cppwg run) — also list the
base class name under `external_bases` so cppwg knows it is registered by an
imported module (names match without template arguments, and with or without
namespace qualification):

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

See the [pybind11 docs on partitioning code over multiple extension modules](https://pybind11.readthedocs.io/en/stable/advanced/misc.html#partitioning-code-over-multiple-extension-modules).

## Excluding inherited overrides

Set `exclude_inherited_overrides: True` (package level) to shrink wrappers.
cppwg then does not emit a binding for a method that merely overrides a virtual
already wrapped on a wrapped base class: pybind11 inheritance plus C++ virtual
dispatch already expose it through the base binding, so the derived `.def` is
pure duplication. The virtual **trampoline** is still generated, so Python
subclasses can still override the method.

A method is skipped only when a wrapped, non-class-excluded base declares a
virtual of the same name, argument types and const-ness (the return type is not
compared, so a covariant-return override still matches). It is kept when: the
base itself excludes the method from wrapping (by name or by type), the base is
in another module that is not `imports`-linked, or another same-name overload on
the class would still be bound (which would otherwise shadow the base). Off by
default.

## Exceptions

To stop C++ exceptions from crashing the Python interpreter, list their class
names under `exceptions`. cppwg generates a pybind11 exception translator for
each. By default the message is read with `what()`; set `message_method` to use a
different accessor:

```yaml
exceptions:
  - name: Exception
    message_method: GetMessage
```

This only applies to thrown C++ exceptions. Errors from C dependencies that use
return codes (e.g. a PETSc `PetscErrorCode`) are not caught unless the wrapped
C++ code converts them into a C++ exception first (for PETSc, via
`PetscCallThrow()` in a C++-exception build, or by checking the code and
throwing). See `PetscUtils::ThrowPetscError` in the cells example.
