# Reference

This page lists every configuration option, with its type and default. Options
fall into two kinds:

- **Common options** may be set at the package, module, or class level and
  **inherit downwards**: a value set on the package applies to every module and
  class in it, unless a lower level overrides it. For example, `auto_includes`
  set at the package level applies to the whole package.

- **Level-specific options** are only meaningful at one level. For example:
  - `modules` at the package level.
  - `imports` at the module level.
  - `name_override` at the class level.

Each table below covers one level; a `–` in the **Default** column marks a
required option.

## Common options

Settable at the package, module, or class level; they inherit downwards.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `arg_type_excludes` | list[str] | `[]` | Skip any method/constructor with an argument type matching one of these. |
| `auto_includes` | bool | `None` | Auto-resolve headers for project types used in wrapped signatures. See [Includes](includes.md#includes). |
| `constructor_arg_type_excludes` | list[str] | `[]` | Skip any constructor with an argument type matching one of these. |
| `constructor_signature_excludes` | list[list[str]] | `[]` | Skip a constructor whose full argument-type list matches an entry. |
| `custom_generator` | str | `""` | Path to a Python template that injects extra binding code. See [Custom generators](custom-generators.md). |
| `discover_arg_excludes` | dict | `{}` | Drop discovered instantiations by template-argument value. See [Templates](templates.md). |
| `discover_template_instantiations` | bool | `None` | Auto-discover explicit instantiations from the source. See [Templates](templates.md). |
| `excluded` | bool | `False` | Exclude the whole class from wrapping. |
| `excluded_methods` | list[str] | `[]` | Method names to skip. |
| `excluded_variables` | list[str] | `[]` | Public data member names to skip (they are otherwise bound with `def_readwrite`/`def_readonly`). |
| `pointer_call_policy` | str | `""` | Default pybind11 `return_value_policy` for methods returning a pointer, e.g. `reference`. |
| `prefix_code` | list[str] | `[]` | Lines emitted before a class's registration block. |
| `prefix_text` | str | `""` | Text emitted at the top of each wrapper file (e.g. a licence header). |
| `reference_call_policy` | str | `""` | Default pybind11 `return_value_policy` for methods returning a reference, e.g. `reference_internal`. |
| `return_type_excludes` | list[str] | `[]` | Skip any method with a return type matching one of these. |
| `smart_ptr_type` | str | `""` | Holder type declared for wrapped classes, e.g. `boost::shared_ptr`. Use one holder consistently across a hierarchy. |
| `source_includes` | list[str] | `[]` | Extra headers to add to the wrapper's `#include` block. |
| `suffix_code` | list[str] | `[]` | Lines emitted after a class's `.def` chain, before the closing `;`. |
| `template_substitutions` | list | `[]` | Explicit template instantiations to wrap. See [Templates](templates.md). |

`CPPWG_SOURCEROOT` in a path value (e.g. in `custom_generator`) is replaced with
the source root directory.

## Package options

Set at the top level of the file.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `common_include_file` | bool | `True` | If true, every wrapper includes a single shared header collection instead of its own headers. Turn **off** so each wrapper includes only what it needs. |
| `exceptions` | list | `[]` | C++ exception classes to translate into Python. See [Exceptions](exceptions.md#exceptions). |
| `exclude_default_args` | bool | `False` | If true, omit C++ default argument values from the generated bindings. |
| `exclude_inherited_overrides` | bool | `False` | If true, skip redundant `.def`s for methods that only override a virtual already wrapped on a wrapped base. See [Excluding inherited overrides](inheritance.md#exclude_inherited_overrides). |
| `modules` | list | – | The modules to build. See [Module options](#module-options). |
| `name` | str | `cppwg_package` | Package name; prepended to every module's extension name (`_{package}_{module}`). |
| `source_cpp_patterns` | list[str] | `["*.cpp"]` | Glob patterns for the source files cppwg scans (used for template-instantiation discovery). |
| `source_hpp_patterns` | list[str] | `["*.hpp"]` | Glob patterns for the header files cppwg scans. |
| `typecasters` | list | `[]` | Type-caster headers to auto-include by type. See [Type casters](includes.md#typecasters). |

All [common options](#common-options) may also be set here.

## Module options

Each entry under `modules:`.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `classes` | list | `[]` | Classes to wrap, or the string `CPPWG_ALL` to wrap every class found. See [Selecting what to wrap](basics.md#selecting-what-to-wrap). |
| `enums` | list | `[]` | Plain (namespace-scope) enums to wrap, or `CPPWG_ALL`. Both unscoped `enum` and scoped `enum class` are supported, e.g. exposed as `Color.RED`. This is the recommended way to wrap an enum. |
| `external_bases` | list[str] | `[]` | Base-class names registered by an imported **package**, so cppwg will emit them as bases. See [Cross-module inheritance](inheritance.md#imports). |
| `free_functions` | list | `[]` | Free functions to wrap, or `CPPWG_ALL`. |
| `imports` | list[str] | `[]` | Python modules to import at the start of this module, so their types are registered first. Required for cross-module inheritance. See [Cross-module inheritance](inheritance.md#imports). |
| `name` | str | `cppwg_module` | Module name; the extension is `_{package}_{name}`. |
| `source_locations` | list[str] | `[]` | Directories (relative to the source root) whose classes this module wraps. |

All [common options](#common-options) may also be set here.

## Class options

Each entry under a module's `classes:`.

Two options point cppwg at an entity's header, and they differ. `source_file` is
a bare **filename** (e.g. `Rectangle.hpp`), resolved via the build's include
path; `source_file_path` is a path **relative to the source root** (e.g.
`primitives/Rectangle.hpp`) that cppwg resolves to a full path and checks exists.
A class is matched to its header automatically — by its name (`Foo` ↔ `Foo.hpp`),
or by `source_file` when the name differs from the filename — so a class usually
needs neither. Free functions and enums are **not** matched this way, so each
must point at its header with `source_file` or `source_file_path` for it to be
parsed (see the sections below).

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | – | The C++ class name (required). |
| `name_override` | str | `""` | Python name for the class, if different from the C++ name. |
| `source_file` | str | `""` | Filename of the header to attribute the class to, when the class name does not match its file name. Emitted as the class's `#include`. |
| `source_file_path` | str | `""` | Path (relative to the source root) to the class's header, resolved and verified — an explicit alternative to the automatic name/`source_file` matching. |

All [common options](#common-options) may also be set here.

:::{note}
A plain `struct` is wrapped here under `classes`, exactly like a class (its
members are public by default). Public **data members** are exposed with
pybind11's `def_readwrite` (or `def_readonly` for a `const` member); use
[`excluded_variables`](#common-options) to suppress a field. Members that have no
takeable pointer-to-member address are skipped automatically: static, bitfield,
C-style array (e.g. `double coords[3]`) and reference members. (The only special
case is a struct wrapping a single nested enum — see the note under
[Enum options](#enum-options).)
:::

## Free function options

Each entry under a module's `free_functions:`. Point cppwg at the function's
header with `source_file` or `source_file_path` so it is parsed — required for an
explicitly listed free function (it is not matched to a header the way a class
is), unless the header is already included by a co-located wrapped class.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | – | The C++ free-function name (required). |
| `source_file` | str | `""` | Filename of the declaring header, resolved via the build's include path. |
| `source_file_path` | str | `""` | Path (relative to the source root) to that header, resolved and verified. Takes precedence over `source_file` if both are set. |

All [common options](#common-options) may also be set here.

## Enum options

Each entry under a module's `enums:`. Point cppwg at the enum's header with
`source_file` or `source_file_path` so it is parsed — required for an explicitly
listed enum, unless the header is already included by a co-located wrapped class.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | – | The C++ enum name (required). |
| `name_override` | str | `""` | Python name for the enum, if different from the C++ name. |
| `source_file` | str | `""` | Filename of the declaring header, resolved via the build's include path. |
| `source_file_path` | str | `""` | Path (relative to the source root) to that header, resolved and verified. Takes precedence over `source_file` if both are set. |
| `export_values` | bool | unset | Whether to emit pybind11's `.export_values()`, which also exposes the enumerators at module scope (e.g. `Color.RED` **and** `RED`). Unset mirrors the C++ enum kind: an unscoped `enum` exports, a scoped `enum class` does not. Set `True`/`False` to force it either way — e.g. `False` to keep an unscoped enum's values off the module scope and avoid name collisions. May also be set at the package or module level to apply to all enums below it (a per-enum value wins). |

All [common options](#common-options) may also be set here.

:::{note}
`enums` is for a **plain, namespace-scope** enum (`enum` or `enum class`). A
struct that wraps a single enum (`struct Foo { enum Value {…}; }`) is a struct, so
it goes under [`classes`](#class-options) instead — the class writer recognises
the pattern and wraps it as an enum. Listing such a struct under `enums` fails (it
is not an enum declaration). The struct-wrapper is a legacy form; prefer a plain
enum here. With `CPPWG_ALL`, each is discovered by its own key — struct-wrappers
via `classes`, plain enums via `enums` — with no overlap.
:::

