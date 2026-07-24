# Tips & recipes

- Use `examples/shapes` or `examples/cells` as a starting point.

- **Incremental rewrites.** By default cppwg only rewrites wrapper files whose
  content has changed, leaving unchanged files untouched so build systems skip
  recompiling them. Pass `--overwrite` to force a full rewrite of all wrapper
  files.

- **One file per templated class.** A templated class's instantiations share a
  single wrapper file: `Foo<2>` and `Foo<3>` are wrapped in one `Foo.cppwg.hpp` /
  `Foo.cppwg.cpp` pair (declaring and defining a `register_Foo_2_class` and
  `register_Foo_3_class` each) rather than a separate file pair per
  instantiation. This reduces the number of generated files and the translation
  units the build has to compile.

- **CastXML flags.** To pass extra flags to the castxml clang frontend (e.g. to
  silence a diagnostic), use `--castxml_cflags`. Values starting with `-` must
  use `=`, e.g. `--castxml_cflags="-Wno-deprecated"`.

- **Consistent smart-pointer holders.** pybind11 requires the same holder type
  across a class hierarchy. Set `smart_ptr_type` once at the package level rather
  than per class, so a base and its derived classes cannot end up with mismatched
  holders (which fails to compile).

- **Unresolved / linker errors after generation** usually mean a wrapped
  signature references a type whose instantiation was never produced. See
  [uninstantiated-dependency dropping](configuration.md#template-instantiations)
  — cppwg drops such instantiations and logs why; instantiate the dependency to
  keep the class.

- See the [pybind11 documentation](https://pybind11.readthedocs.io/) for help
  writing and understanding the generated wrapper code.
