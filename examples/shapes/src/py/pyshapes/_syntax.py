from collections.abc import Iterable


def _normalize_key(key):
    """Normalize a template-argument subscript key to a tuple of strings.

    A scalar key becomes a 1-tuple; each argument maps to its ``__name__`` (for a
    class) or ``str`` otherwise - so ``Point[2]`` and ``MacroMesh[2, 2]`` and
    ``CellFactory[Cell, 2]`` all key the same way the wrapped names were built. A
    string is treated as a single scalar (not iterated character by character).
    """
    if isinstance(key, str) or not isinstance(key, Iterable):
        key = (key,)
    return tuple(arg.__name__ if hasattr(arg, "__name__") else str(arg) for arg in key)


class TemplateClass:
    """Base for a stub class that gives a templated class subscript syntax.

    Subclass it with an ``_instantiations`` map from template-argument tuples to
    the concrete wrapped classes; ``Foo[args]`` then resolves the instantiation -
    e.g. ``Point[2]`` -> ``Point_2`` - mirroring how ``list[int]`` works via
    ``__class_getitem__``. Subclassing (rather than an instance) makes ``Foo`` a
    real class object. Keys are normalized once at subclass creation.
    """

    _instantiations: dict = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._instantiations = {
            _normalize_key(args): cls_ for args, cls_ in cls._instantiations.items()
        }

    def __class_getitem__(cls, key):
        return cls._instantiations[_normalize_key(key)]


class TemplateMethod:
    """Subscript syntax for a templated method (the method analogue of
    TemplateClass).

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

    def __getitem__(self, key):
        # Mangled binding is <base>_<arg1>_<arg2>..., matching cppwg's Foo_2 style.
        suffix = "_" + "_".join(_normalize_key(key))
        return getattr(self._target, self._base_name + suffix)
