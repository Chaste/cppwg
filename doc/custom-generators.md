# Custom generators

Some bindings cannot be produced from the parsed C++ signatures alone — for
example a `.def` built from a hard-coded list, or a template-method instantiation
like `AddCellWriter<CellAgesWriter>`. A **custom generator** lets you inject
hand-written binding code for a class while cppwg generates the rest.

Point a class at a generator with `custom_generator`:

```yaml
- name: MeshBasedCellPopulation
  custom_generator: "CPPWG_SOURCEROOT/wrapper/PopulationWriterCustomTemplate.py"
```

`CPPWG_SOURCEROOT` is replaced with the source root directory. The file defines a
subclass of `cppwg.templates.custom.Custom`, overriding the hooks it needs.

## Hooks

| Hook | Injects | Where |
| --- | --- | --- |
| `get_class_cpp_pre_code(class_name)` | Code before the registration block | Before `py::class_<...>` |
| `get_class_cpp_def_code(class_name)` | Extra `.def(...)` lines | Into the `.def` chain |
| `get_source_includes()` | Header names the emitted code needs | The wrapper `#include` block |

`class_name` is the wrapper alias for the current instantiation (e.g.
`Foo_2_2`), so pre-code and def-code can refer to the class by that name.

## Injecting `.def` code

```python
import cppwg.templates.custom


class PopulationWriterCustomTemplate(cppwg.templates.custom.Custom):
    WRITERS = ["CellAgesWriter", "CellIdWriter"]

    def get_class_cpp_def_code(self, class_name):
        return "".join(
            f'.def("AddCellWriter{w}", &{class_name}::AddCellWriter<{w}>)\n'
            for w in self.WRITERS
        )
```

## Declaring the headers your code needs

Code emitted by a generator can reference types cppwg never sees in the parsed
signatures, so [`auto_includes`](configuration.md#includes) cannot resolve their
headers and they would otherwise have to be repeated under `source_includes`.
Override `get_source_includes()` to return the header names — spelled as under
`source_includes`, a bare name like `Foo.hpp` (cppwg adds the quotes) or an
angle-bracket string like `<foo>`. cppwg adds them to the wrapper's `#include`
block (deduplicated), so the generator and the includes its code needs live in
one place:

```python
class PopulationWriterCustomTemplate(cppwg.templates.custom.Custom):
    WRITERS = ["CellAgesWriter", "CellIdWriter"]

    def get_class_cpp_def_code(self, class_name):
        return "".join(
            f'.def("AddCellWriter{w}", &{class_name}::AddCellWriter<{w}>)\n'
            for w in self.WRITERS
        )

    def get_source_includes(self, *args, **kwargs):
        return [f"{w}.hpp" for w in self.WRITERS]
```

See the `MutableElement`, `ReplicatableVector`, and population classes in
`examples/cells/dynamic/config.yaml` and their generator templates for full
examples.
