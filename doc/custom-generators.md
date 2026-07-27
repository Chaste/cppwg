# Custom generators

Some bindings cannot be produced from the parsed C++ signatures alone — for
example a `.def` built from a hard-coded list, or a template-method instantiation
like `AddMesh<PottsMesh>`. A **custom generator** lets you inject
hand-written binding code for a class while cppwg generates the rest.

Point a class at a generator with `custom_generator`:

```yaml
- name: MeshCollection
  custom_generator: "CPPWG_SOURCEROOT/wrapper/custom/MeshCollectionTemplate.py"
```

`CPPWG_SOURCEROOT` is replaced with the source root directory. The file defines a
subclass of `cppwg.templates.custom.Custom`, overriding the hooks it needs. Set
`custom_generator` on a module instead to use the module-level hooks below.

## Hooks

Override only the hooks you need. Class-level hooks fire for a generator set on a
class; module-level hooks fire for one set on a module.

| Hook | Scope | Injects | Where |
| --- | --- | --- | --- |
| `get_class_cpp_pre_code(class_name)` | class | Code before the registration block | Before `py::class_<...>` |
| `get_class_cpp_def_code(class_name)` | class | Extra `.def(...)` lines | Into the `.def` chain |
| `get_class_cpp_source_includes()` | class | Header names the emitted code needs | The wrapper `#include` block |
| `get_module_pre_code()` | module | Top-of-file code | Before the class includes |
| `get_module_code()` | module | Module-body code | Before the end of `PYBIND11_MODULE` |

`class_name` is the wrapper alias for the current instantiation (e.g. `Foo_2_2`),
so class-level pre-code and def-code can refer to the class by that name.

## Injecting wrapper code

The generator below adds a custom `.def` for each mesh type (`AddMesh_PottsMesh`
and `AddMesh_MacroMesh`) from the templated `AddMesh<...>` method:

```python
import cppwg.templates.custom


class MeshCollectionTemplate(cppwg.templates.custom.Custom):
    MESHES = ["PottsMesh", "MacroMesh"]

    def get_class_cpp_def_code(self, class_name):
        return "".join(
            f'.def("AddMesh_{m}", &{class_name}::AddMesh<{m}>)\n'
            for m in self.MESHES
        )
```

## Injecting headers

Code emitted by a generator can reference types that never appear in the parsed
signatures, so [`auto_includes`](includes.md#auto_includes) cannot resolve their
headers, and they would otherwise have to be listed manually under
`source_includes`. Override `get_class_cpp_source_includes()` on the same generator to
declare them:

```python
    def get_class_cpp_source_includes(self, *args, **kwargs):
        return [f"{m}.hpp" for m in self.MESHES]
```

:::{seealso}
See [Reference](reference.md) for the `custom_generator` option.
:::
