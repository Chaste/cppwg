"""Unit tests for cppwg.writers.method_writer exclusion behaviour."""

from cppwg.writers.method_writer import CppMethodWrapperWriter


class _Type:
    """Stand-in for a pygccxml type (only decl_string is used)."""

    def __init__(self, decl_string):
        self.decl_string = decl_string


class _Method:
    """Minimal member_function_t stand-in."""

    def __init__(self, name, return_type, arg_types, parent, access="public"):
        self.name = name
        self.return_type = _Type(return_type)
        self.argument_types = [_Type(a) for a in arg_types]
        self.access_type = access
        self.parent = parent


class _ClassInfo:
    """Minimal CppClassInfo stand-in for exclusion lookups."""

    def __init__(self, excludes=None, excluded_methods=None):
        self._excludes = excludes or {}
        self.excluded_methods = excluded_methods or []

    def hierarchy_attribute_gather_flat(self, name):
        return list(self._excludes.get(name, []))


def _writer(class_info, return_type="void", arg_types=(), access="public"):
    class_decl = object()
    method = _Method("Foo", return_type, list(arg_types), class_decl, access)
    writer = object.__new__(CppMethodWrapperWriter)
    writer.class_info = class_info
    writer.method_decl = method
    writer.class_decl = class_decl
    return writer


def test_arg_type_exclude_respects_identifier_boundaries():
    """A method taking the excluded arg type is dropped; a look-alike is kept."""
    class_info = _ClassInfo(excludes={"arg_type_excludes": ["Shape"]})

    assert _writer(class_info, arg_types=["::Shape<2> const &"]).exclude() is True
    assert (
        _writer(class_info, arg_types=["::AbstractShape<2> const &"]).exclude() is False
    )
    assert _writer(class_info, arg_types=["int"]).exclude() is False


def test_return_type_exclude():
    """return_type_excludes drops methods by return type only."""
    class_info = _ClassInfo(excludes={"return_type_excludes": ["RawPtr"]})

    assert _writer(class_info, return_type="::RawPtr *").exclude() is True
    assert _writer(class_info, return_type="int").exclude() is False
    # A return-type pattern does not exclude on arguments.
    assert _writer(class_info, arg_types=["::RawPtr *"]).exclude() is False


def test_calldef_exclude_applies_to_both_return_and_args():
    """The deprecated calldef_excludes matches both return and argument types."""
    class_info = _ClassInfo(excludes={"calldef_excludes": ["Foo"]})

    assert _writer(class_info, return_type="::Foo &").exclude() is True
    assert _writer(class_info, arg_types=["::Foo const &"]).exclude() is True
    assert (
        _writer(class_info, return_type="int", arg_types=["double"]).exclude() is False
    )


from string import Template  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from cppwg.writers import method_writer as method_writer_module  # noqa: E402


class _Arg:
    def __init__(self, name, default_value=None, decl_type="int"):
        self.name = name
        self.default_value = default_value
        self.decl_type = decl_type


class _RichMethod:
    def __init__(self, name="bar", return_type="void", arg_types=(), arguments=(),
                 parent=None, access="public", has_static=False, has_const=False,
                 virtuality="not virtual"):
        self.name = name
        self.return_type = _Type(return_type)
        self.argument_types = [_Type(a) for a in arg_types]
        self.arguments = list(arguments)
        self.parent = parent
        self.access_type = access
        self.has_static = has_static
        self.has_const = has_const
        self.virtuality = virtuality


_CLASS_METHOD_TPL = Template(
    '.def$def_adorn("$method_name", '
    "($return_type($self_ptr)($arg_signature)$const_adorn) "
    "&${class_py_name}::$method_name$default_args$call_policy)"
)
_OVERRIDE_TPL = Template(
    "$return_type $method_name($arg_string)$const_adorn override "
    "{ PYBIND11_OVERRIDE$overload_adorn($tidy_method_name, $class_py_name, "
    "$method_name, $args_string); }"
)


def _make_writer(method, attrs=None, template_params=None, template_arg_lists=None):
    class_decl = SimpleNamespace(name="Foo")
    method.parent = class_decl
    class_info = _ClassInfo()
    class_info.decls = [class_decl]
    class_info.py_names = ["Foo_2"]
    class_info.template_params = template_params
    class_info.template_arg_lists = template_arg_lists
    class_info.name = "Foo"
    class_info.hierarchy_attribute = lambda name, _a=attrs or {}: _a.get(name)
    templates = {"class_method": _CLASS_METHOD_TPL, "method_virtual_override": _OVERRIDE_TPL}
    return CppMethodWrapperWriter(class_info, 0, method, templates)


# --- __init__ ---
def test_init_uses_py_name_and_template_args():
    class_decl = SimpleNamespace(name="Foo")
    class_info = SimpleNamespace(
        decls=[class_decl], py_names=["Foo_2"],
        template_params=["DIM"], template_arg_lists=[["2"]],
    )
    writer = CppMethodWrapperWriter(class_info, 0, _RichMethod(parent=class_decl), {})
    assert writer.class_py_name == "Foo_2"
    assert writer.template_args == ["2"]


def test_init_falls_back_to_decl_name():
    class_decl = SimpleNamespace(name="Foo")
    class_info = SimpleNamespace(
        decls=[class_decl], py_names=[None],
        template_params=None, template_arg_lists=None,
    )
    writer = CppMethodWrapperWriter(class_info, 0, _RichMethod(parent=class_decl), {})
    assert writer.class_py_name == "Foo"
    assert writer.template_args is None


# --- remaining exclude() branches ---
def test_exclude_named_method():
    class_info = _ClassInfo(excluded_methods=["Foo"])
    assert _writer(class_info).exclude() is True


def test_exclude_private_method():
    assert _writer(_ClassInfo(), access="private").exclude() is True


def test_exclude_subclass_method():
    writer = _writer(_ClassInfo())
    writer.method_decl.parent = object()  # parent differs from class_decl
    assert writer.exclude() is True


# --- generate_wrapper ---
def test_generate_wrapper_instance_method_with_default():
    method = _RichMethod(
        name="bar", return_type="void", arg_types=["int"],
        arguments=[_Arg("i", default_value="(-1)", decl_type="int")],
    )
    result = _make_writer(method).generate_wrapper()
    assert '.def("bar", (void(Foo_2::*)(int)) &Foo_2::bar, py::arg("i") = -1)' == result


def test_generate_wrapper_static_method():
    method = _RichMethod(name="make", has_static=True)
    result = _make_writer(method).generate_wrapper()
    assert '.def_static("make", (void(*)()) &Foo_2::make)' == result


def test_generate_wrapper_const_method():
    method = _RichMethod(name="size", return_type="unsigned", has_const=True)
    result = _make_writer(method).generate_wrapper()
    assert "(unsigned(Foo_2::*)() const)" in result


def test_generate_wrapper_excluded_returns_empty():
    method = _RichMethod(name="bar", access="private")
    assert _make_writer(method).generate_wrapper() == ""


def test_generate_wrapper_pointer_call_policy(monkeypatch):
    monkeypatch.setattr(method_writer_module.type_traits, "is_pointer", lambda rt: True)
    monkeypatch.setattr(method_writer_module.type_traits, "is_reference", lambda rt: False)
    method = _RichMethod(name="get", return_type="Foo *")
    writer = _make_writer(method, attrs={"pointer_call_policy": "reference"})
    assert ", py::return_value_policy::reference)" in writer.generate_wrapper()


def test_generate_wrapper_reference_call_policy(monkeypatch):
    monkeypatch.setattr(method_writer_module.type_traits, "is_pointer", lambda rt: False)
    monkeypatch.setattr(method_writer_module.type_traits, "is_reference", lambda rt: True)
    method = _RichMethod(name="ref", return_type="Foo &")
    writer = _make_writer(method, attrs={"reference_call_policy": "reference_internal"})
    assert ", py::return_value_policy::reference_internal)" in writer.generate_wrapper()


def test_generate_wrapper_substitutes_template_param():
    method = _RichMethod(
        name="fill", arg_types=["unsigned"],
        arguments=[_Arg("n", default_value="DIM", decl_type="unsigned")],
    )
    writer = _make_writer(method, template_params=["DIM"], template_arg_lists=[["2"]])
    assert 'py::arg("n") = 2' in writer.generate_wrapper()


# --- generate_virtual_override_wrapper ---
def test_generate_virtual_override_pure():
    method = _RichMethod(
        name="area", return_type="double",
        arg_types=["int", "bool"],
        arguments=[_Arg("a"), _Arg("b")],
        virtuality="pure virtual",
    )
    result = _make_writer(method).generate_virtual_override_wrapper()
    assert "PYBIND11_OVERRIDE_PURE(" in result
    assert "double area(int a, bool b) override" in result


def test_generate_virtual_override_non_pure_const():
    method = _RichMethod(name="run", return_type="void", has_const=True)
    result = _make_writer(method).generate_virtual_override_wrapper()
    assert "PYBIND11_OVERRIDE(" in result
    assert "void run() const override" in result


def test_generate_virtual_override_excluded_returns_empty():
    method = _RichMethod(name="run", access="private")
    assert _make_writer(method).generate_virtual_override_wrapper() == ""


def test_generate_wrapper_pointer_return_without_policy(monkeypatch):
    """A pointer return with no configured call policy emits no policy clause."""
    monkeypatch.setattr(method_writer_module.type_traits, "is_pointer", lambda rt: True)
    monkeypatch.setattr(method_writer_module.type_traits, "is_reference", lambda rt: False)
    method = _RichMethod(name="get", return_type="Foo *")
    result = _make_writer(method, attrs={}).generate_wrapper()  # no pointer_call_policy
    assert "return_value_policy" not in result
