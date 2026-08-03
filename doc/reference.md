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

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | – | The C++ class name (required). |
| `name_override` | str | `""` | Python name for the class, if different from the C++ name. |
| `source_file` | str | `""` | Header to attribute the class to, when the class name does not match its file name. |

All [common options](#common-options) may also be set here.

## Enum options

Each entry under a module's `enums:`.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `name` | str | – | The C++ enum name (required). |
| `name_override` | str | `""` | Python name for the enum, if different from the C++ name. |
| `source_file_path` | str | `""` | Path (relative to the source root) to the header declaring the enum, so it is parsed. Required for an explicitly listed enum unless its header is already pulled in by a wrapped class in the same header. |

All [common options](#common-options) may also be set here.

