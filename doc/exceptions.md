# Exceptions

To stop custom C++ exceptions from crashing the Python interpreter, list their
class names under `exceptions`. cppwg generates a pybind11 translator that catches
each one and re-raises it in Python as a `RuntimeError` carrying the exception's
message. The message is read with `what()` by default; set `message_method` to
use a different accessor.

An entry may be a bare class name, or a mapping that overrides the message
method:

```yaml
exceptions:
  - Exception                    # message read with what()
  - name: CellsException
    message_method: GetMessage   # message read with GetMessage()
```

:::{caution}
This only applies to thrown C++ exceptions. Errors from C dependencies that use
return codes (e.g. a `PetscErrorCode`) are not caught unless the underlying
C++ code converts them into a C++ exception first. See
`PetscUtils::ThrowPetscError` in the cells example.
:::

:::{seealso}
- See the [pybind11 docs](https://pybind11.readthedocs.io/en/stable/advanced/exceptions.html)
on exceptions.
- See [Reference](reference.md) for a list of all configuration options.
:::
