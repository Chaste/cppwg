import inspect
from collections.abc import Iterable


class TemplateClassDict:
    def __init__(self, template_dict):
        self._dict = {}
        for arg_tuple, cls in template_dict.items():
            if not inspect.isclass(cls):
                raise TypeError(f"Expected class, got {type(cls)}")
            if not isinstance(arg_tuple, Iterable):
                arg_tuple = (arg_tuple,)
            key = tuple(
                arg.__name__ if inspect.isclass(arg) else str(arg) for arg in arg_tuple
            )
            self._dict[key] = cls

    def __getitem__(self, arg_tuple):
        if not isinstance(arg_tuple, Iterable):
            arg_tuple = (arg_tuple,)
        key = tuple(
            arg.__name__ if inspect.isclass(arg) else str(arg) for arg in arg_tuple
        )
        return self._dict[key]


class TemplateMethod:
    """Subscript syntax for a templated method (the method analogue of
    TemplateClassDict).

    Assign it as a class attribute so ``obj.<base>[Arg]()`` dispatches to the
    mangled binding ``obj.<base><Arg>()`` that cppwg generates for the templated
    C++ method ``<base><Arg>()`` - e.g. ``pop.AddCellWriter[CellVolumesWriter]()``
    calls ``pop.AddCellWriterCellVolumesWriter()``. Each subscript argument maps
    to its ``__name__`` (for a class) or ``str`` (otherwise), matching the suffix
    cppwg appends when naming the instantiated method.
    """

    def __init__(self, base_name):
        self._base_name = base_name

    def __get__(self, obj, owner=None):
        return _BoundTemplateMethod(obj if obj is not None else owner, self._base_name)


class _BoundTemplateMethod:
    def __init__(self, target, base_name):
        self._target = target
        self._base_name = base_name

    def __getitem__(self, arg_tuple):
        if not isinstance(arg_tuple, Iterable):
            arg_tuple = (arg_tuple,)
        suffix = "".join(
            arg.__name__ if inspect.isclass(arg) else str(arg) for arg in arg_tuple
        )
        return getattr(self._target, self._base_name + suffix)
