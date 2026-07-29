"""Unit tests for cppwg.writers.free_function_writer exclusion behaviour."""

from cppwg.writers.free_function_writer import CppFreeFunctionWrapperWriter


class _Type:
    """Stand-in for a pygccxml type (only decl_string is used)."""

    def __init__(self, decl_string):
        self.decl_string = decl_string


class _Decl:
    """Minimal free_function_t stand-in."""

    def __init__(self, return_type, arg_types):
        self.return_type = _Type(return_type)
        self.argument_types = [_Type(a) for a in arg_types]


class _FreeFunctionInfo:
    """Minimal CppFreeFunctionInfo stand-in for exclusion lookups."""

    def __init__(self, return_type, arg_types, excludes=None):
        self.decls = [_Decl(return_type, arg_types)]
        self._excludes = excludes or {}

    def hierarchy_attribute_gather_flat(self, name):
        return list(self._excludes.get(name, []))


def _writer(return_type="void", arg_types=(), excludes=None):
    info = _FreeFunctionInfo(return_type, list(arg_types), excludes)
    writer = object.__new__(CppFreeFunctionWrapperWriter)
    writer.free_function_info = info
    return writer


def test_free_function_arg_type_exclude_respects_boundaries():
    """arg_type_excludes drops free functions by argument type, as a whole token."""
    excludes = {"arg_type_excludes": ["Node"]}

    assert _writer(arg_types=["::Node<2> const &"], excludes=excludes).exclude() is True
    assert (
        _writer(arg_types=["::AbstractNode<2> const &"], excludes=excludes).exclude()
        is False
    )


def test_free_function_return_type_exclude():
    """return_type_excludes drops free functions by return type only."""
    excludes = {"return_type_excludes": ["RawPtr"]}

    assert _writer(return_type="::RawPtr *", excludes=excludes).exclude() is True
    assert _writer(return_type="int", excludes=excludes).exclude() is False
    assert _writer(arg_types=["::RawPtr *"], excludes=excludes).exclude() is False


def test_free_function_calldef_exclude_applies_to_both():
    """The deprecated calldef_excludes matches both return and argument types."""
    excludes = {"calldef_excludes": ["Foo"]}

    assert _writer(return_type="::Foo &", excludes=excludes).exclude() is True
    assert _writer(arg_types=["::Foo const &"], excludes=excludes).exclude() is True


def test_free_function_not_excluded_without_options():
    """With no exclusion options set, nothing is excluded."""
    assert _writer(return_type="int", arg_types=["double"]).exclude() is False


from string import Template  # noqa: E402


class _Arg:
    """Stand-in for a pygccxml argument (name, default, decl_type)."""

    def __init__(self, name, default_value=None, decl_type="int"):
        self.name = name
        self.default_value = default_value
        self.decl_type = decl_type


class _FullDecl(_Decl):
    """A free_function_t stand-in that also carries a name and arguments."""

    def __init__(self, name, arguments, return_type="void", arg_types=()):
        super().__init__(return_type, list(arg_types))
        self.name = name
        self.arguments = arguments


class _FullInfo(_FreeFunctionInfo):
    def __init__(self, decl, excludes=None, exclude_default_args=False):
        super().__init__("void", [], excludes)
        self.decls = [decl]
        self._exclude_default_args = exclude_default_args

    def hierarchy_attribute(self, name):
        if name == "exclude_default_args":
            return self._exclude_default_args
        return None


def test_generate_wrapper_builds_def_with_default_args():
    """A def line is built with normalized py::arg default values."""
    templates = {
        "free_function": Template('.def("$function_name", &$function_name$default_args)')
    }
    decl = _FullDecl("my_func", [_Arg("count", default_value="(-1)", decl_type="int")])
    writer = CppFreeFunctionWrapperWriter(_FullInfo(decl), templates)

    result = writer.generate_wrapper()

    assert result == '.def("my_func", &my_func, py::arg("count") = -1)'


def test_generate_wrapper_excluded_returns_empty():
    """An excluded free function generates no wrapper code."""
    templates = {"free_function": Template("$function_name")}
    decl = _FullDecl("f", [], return_type="::Bad *")
    info = _FullInfo(decl, excludes={"return_type_excludes": ["Bad"]})

    assert CppFreeFunctionWrapperWriter(info, templates).generate_wrapper() == ""


def test_generate_wrapper_omits_defaults_when_option_set():
    """exclude_default_args suppresses the py::arg default clauses."""
    templates = {"free_function": Template("$function_name|$default_args")}
    decl = _FullDecl("f", [_Arg("x", default_value="1")])
    info = _FullInfo(decl, exclude_default_args=True)

    assert CppFreeFunctionWrapperWriter(info, templates).generate_wrapper() == "f|"


def test_generate_wrapper_arg_without_default_value():
    """An argument with no default contributes a bare py::arg."""
    templates = {"free_function": Template("$default_args")}
    decl = _FullDecl("f", [_Arg("x", default_value=None)])
    info = _FullInfo(decl)

    assert CppFreeFunctionWrapperWriter(info, templates).generate_wrapper() == (
        ', py::arg("x")'
    )


def test_generate_wrapper_keeps_non_numeric_default():
    """A default value that is not a number is emitted verbatim."""
    templates = {"free_function": Template("$default_args")}
    decl = _FullDecl("f", [_Arg("mode", default_value='"auto"', decl_type="std::string")])
    result = CppFreeFunctionWrapperWriter(_FullInfo(decl), templates).generate_wrapper()
    assert result == ', py::arg("mode") = "auto"'
