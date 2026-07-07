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
