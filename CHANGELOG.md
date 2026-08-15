# Changelog

Notable changes made to cppwg in each release.

## [Unreleased]

## [0.5.0] - 2026-08-15

### Added

- Automatic discovery of explicit C++ template instantiations: the
  `discover_template_instantiations` option (scan the sources for
  `template class Foo<2>;`), the package-level `source_cpp_patterns` glob
  (default `["*.cpp"]`) naming which sources to scan, and `discover_arg_excludes`
  (e.g. `{SPACE_DIM: [1]}`) to drop unwanted discovered instantiations by named
  template parameter (#73).
- `auto_includes` option to auto-include project-type headers, including
  template-argument types (#97).
- `typecasters` option to auto-include pybind11 typecasters (#95).
- `exclude_inherited_overrides` option to skip redundant inherited-override
  `.def`s (#101).
- Enum wrapping: a module-level `enums` config list with an `export_values`
  option controlling `.def(py::enum_...).export_values()` for unscoped enums (#113).
- Struct wrapping and public data-member exposure (#116).
- A `get_class_cpp_source_includes` hook for custom generators, allowing them to
  declare their own C++ class source includes (#99).
- Templated Python call syntax: `TemplateClass` (`Foo[2]`) and `TemplateMethod`
  (`obj.Bar[T]()`) descriptors, wired into the shapes and cells examples (#70).
- `cppwg genpackage` subcommand that generates a Python package layer from the
  wrapper config. cppwg emits a `cppwg_package_model.json` describing the wrapped
  modules and classes; `genpackage` turns that plus a `package_layout.yaml` into a
  per-subpackage `_generated.py` (#102).
- Coverage measurement via Codecov, targeting ~99% (#20).
- Logfile rotation for the `-l`/`--logfile` option.
- Support for Python 3.14 (#130).

### Changed

- Consolidated a templated class's instantiations into a single wrapper file pair
  (`Foo.cppwg.cpp` / `Foo.cppwg.hpp`) instead of one pair per instantiation
  (`Foo_2.cppwg.cpp`, `Foo_3.cppwg.cpp`, ...); the generated Python class names
  (`Foo_2`, `Foo_3`) are unchanged (#30).
- Replaced the hand-written `TemplateClassDict` scaffolding in the shapes and
  cells examples with a generated `TemplateClass` stub. `TemplateClassDict` was a
  module-level dict-like instance, so `Foo` was not a class; `TemplateClass` is
  subclassed, making `Foo` a real class object that resolves `Foo[2]` via
  `__class_getitem__` (like `list[int]`) (#70).
- Sped up wrapper generation with a base-class virtual-signature index and
  caching in the inherited-override check (#125).
- Scoped source collection to the project's own source: CMake build trees are
  pruned from the walk (any directory containing a `CMakeCache.txt`, assuming an
  out-of-source build), and the explicit-instantiation scan is restricted to the
  module `source_locations` when set. Previously a same-named class from a
  vendored dependency or example tree under the source root could be conflated
  with a wrapped class and corrupt its discovered/pruned template instantiations
  (#125).
- Unified the C++ argument/return exclusion options (`arg_type_excludes`,
  `return_type_excludes`, `constructor_arg_type_excludes`) and applied them to
  free functions as well as class methods and constructors (#91).
- Housekeeping: consolidated duplicated logic into helpers, including exclusion
  predicates, a single `BASE_INFO_OPTIONS` schema, and shared default-argument,
  registration-name, and wrapper-filename helpers (#119).

### Deprecated

- `calldef_excludes`: use `arg_type_excludes` and/or `return_type_excludes`
  instead. The parser now warns when it is used; it is still honoured as both
  `arg_type_excludes` and `return_type_excludes` for backward compatibility
  (#91).

### Removed

- The unused `extra_code` config option; use `prefix_code` / `suffix_code` (#92).

### Fixed

- `exclude_inherited_overrides` set at module or class level was silently ignored
  (only package level was parsed) (#101).
- A `KeyError` when a config listed explicit variables, a dead generated-file
  skip in source collection, and a crash in the default `PackageInfo` when no
  config file was given (#20).

## [0.4.1] - 2026-06-30

### Added

- Cross-module inheritance (#88, #89).

## [0.4.0] - 2026-06-29

### Added

- `--castxml_cflags` option (#78).
- `--overwrite` option (#82).
- Support for custom C++ exception classes (#84).

### Changed

- Dropped Python 3.8 and 3.9; added support for Python 3.13 (#76).
- Switched the example projects' conda builds to rattler-build (#80).

### Fixed

- Handling of numeric arguments (#67, #68, #69).

## [0.3.4] - 2024-11-22

### Added

- `--castxml_compiler` option (#66).

### Changed

- castxml is now a system requirement rather than being installed automatically
  from pip; clang is now a recommended system dependency (#66).

## [0.3.3] - 2024-11-13

### Fixed

- Stabilised class sorting for deterministic wrapper output (#65).

## [0.3.2] - 2024-11-08

### Added

- Example conda build, with typecaster examples for PETSc, VTK and Boost uBLAS
  (#63).

## [0.3.1] - 2024-10-08

### Changed

- The example template-class syntax accepts types in arguments (#62).

## [0.3.0] - 2024-09-30

### Breaking Changes

- The Python name format for a templated class `Foo<A,B>` changes from `FooA_B`
  to `Foo_A_B` (#55).
- Wrapper module names changed from `<module>.main.cpp` to
  `_<package>_<module>.main.cppwg.cpp`, and a `.cppwg` extension was added to
  `wrapper_header_collection.cppwg.hpp` (#58).

### Added

- Example of `Foo[2,2]`-style syntax for templated classes, and a
  `source_file_path` config key (#60).

### Changed

- Cosmetic enhancements to the generated wrappers, and updates to YAML parsing
  (#55, #56, #59, #61).

## [0.2.1] - 2024-09-23

### Added

- Automatic sorting of classes by dependence (#53, #54).

### Changed

- Console log level is `ERROR` with `--quiet`, otherwise `INFO`; the file log
  level is always `INFO` (#52).

## [0.2.0] - 2024-09-16

### Added

- Prefix text for generated wrappers.
- Excluding classes from wrapping via the `excluded` config key.
- Listing of unknown classes in the logs.
- Log output to a file via `--logfile`.
- pybind11 fetched with CMake `FetchContent` in the example.

## [0.1.0] - 2024-08-05

### Added

- Excluding constructors by signature (#47).
- Prefix text for generated wrappers (#48).

### Fixed

- Template parameters in method default arguments (#44).
- Wrappers for initializer lists of the form `foo = {}` in method default
  arguments (#45).

## [0.0.1] - 2024-05-07

### Added

- Locally pip-installable via `pip install .` and callable from the command line.
- Tested on Python 3.8 to 3.12.

### Fixed

- Compatibility with C++ standards later than C++11.
- Wrapping of templated classes with only a single explicit instantiation.
- Wrapping of templated classes with signatures like `template <type A, B=A>`.
- Handling of template parameters in method default arguments.

## [0.0.1-alpha] - 2024-03-12

Initial release.

[Unreleased]: https://github.com/Chaste/cppwg/compare/v0.5.0...develop
[0.5.0]: https://github.com/Chaste/cppwg/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/Chaste/cppwg/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Chaste/cppwg/compare/v0.3.4...v0.4.0
[0.3.4]: https://github.com/Chaste/cppwg/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/Chaste/cppwg/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/Chaste/cppwg/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Chaste/cppwg/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Chaste/cppwg/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Chaste/cppwg/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Chaste/cppwg/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Chaste/cppwg/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/Chaste/cppwg/compare/v0.0.1-alpha...v0.0.1
[0.0.1-alpha]: https://github.com/Chaste/cppwg/releases/tag/v0.0.1-alpha
