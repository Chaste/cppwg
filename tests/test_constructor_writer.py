"""Unit tests for cppwg.writers.constructor_writer exclusion behaviour."""

from cppwg.info import exclusions as exclusions_module
from cppwg.info.base_info import BaseInfo
from cppwg.writers.constructor_writer import CppConstructorWrapperWriter


class _Type:
    """Stand-in for a pygccxml type (only decl_string is used)."""

    def __init__(self, decl_string):
        self.decl_string = decl_string


class _ClassDecl:
    """Minimal class_t stand-in for the early checks in exclude()."""

    is_abstract = False
    recursive_bases = []

    def member_functions(self, allow_empty=True):
        return []


class _CtorDecl:
    """Minimal constructor_t stand-in."""

    is_artificial = False

    def __init__(self, arg_types, parent):
        self.argument_types = [_Type(a) for a in arg_types]
        self.parent = parent


class _ClassInfo:
    """Minimal CppClassInfo stand-in that mirrors production gathering."""

    def __init__(self, signature_excludes=None):
        self._signature_excludes = signature_excludes

    def hierarchy_attribute_gather(self, name):
        if name == "constructor_signature_excludes" and self._signature_excludes:
            return [self._signature_excludes]
        return []

    # Borrow production so the double cannot diverge (scalar handling etc.).
    hierarchy_attribute_gather_flat = BaseInfo.hierarchy_attribute_gather_flat


def _writer(arg_types, signature_excludes, monkeypatch):
    # is_copy_constructor inspects a real pygccxml decl; stub it out so exclude()
    # reaches the signature-exclude loop with our lightweight fakes.
    monkeypatch.setattr(
        exclusions_module.type_traits_classes,
        "is_copy_constructor",
        lambda decl: False,
    )
    class_decl = _ClassDecl()
    writer = object.__new__(CppConstructorWrapperWriter)
    writer.class_info = _ClassInfo(signature_excludes)
    writer.class_decl = class_decl
    writer.ctor_decl = _CtorDecl(arg_types, parent=class_decl)
    return writer


def test_signature_exclude_matches_valid_signature(monkeypatch):
    """A well-formed nested signature excludes a matching constructor."""
    writer = _writer(["int", "int", "int"], [["int", "int", "int"]], monkeypatch)
    assert writer.exclude() is True


def test_signature_exclude_skips_scalar_int(monkeypatch):
    """A mis-typed scalar (constructor_signature_excludes: 5) is skipped, not len()'d."""
    writer = _writer(["int", "int", "int"], 5, monkeypatch)
    assert writer.exclude() is False


def test_signature_exclude_skips_scalar_string(monkeypatch):
    """A mis-typed scalar string is skipped, not iterated character by character."""
    writer = _writer(["int", "int", "int"], "int", monkeypatch)
    assert writer.exclude() is False


from string import Template  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from pygccxml.declarations import type_traits  # noqa: E402


class _MemberFn:
    def __init__(self, virtuality="not virtual", access_type="public"):
        self.virtuality = virtuality
        self.access_type = access_type


class _RichClassDecl:
    def __init__(
        self, name="Foo", member_fns=(), is_abstract=False, recursive_bases=()
    ):
        self.name = name
        self._mfs = list(member_fns)
        self.is_abstract = is_abstract
        self.recursive_bases = list(recursive_bases)

    def member_functions(self, allow_empty=True):
        return self._mfs


class _Arg:
    def __init__(self, name, default_value=None, decl_type="int"):
        self.name = name
        self.default_value = default_value
        self.decl_type = decl_type


class _RichCtor:
    def __init__(self, arg_types=(), arguments=(), parent=None, is_artificial=False):
        self.argument_types = [_Type(a) for a in arg_types]
        self.arguments = list(arguments)
        self.parent = parent
        self.is_artificial = is_artificial


def _no_copy_ctor(monkeypatch):
    # The artificial-copy-constructor check moved to cppwg.info.exclusions.
    monkeypatch.setattr(
        exclusions_module.type_traits_classes,
        "is_copy_constructor",
        lambda decl: False,
    )


def test_init_reads_template_metadata():
    class_decl = _RichClassDecl(name="Foo")
    class_info = SimpleNamespace(
        decls=[class_decl],
        py_names=["Foo_2"],
        template_params=["DIM"],
        template_arg_lists=[["2"]],
    )
    writer = CppConstructorWrapperWriter(
        class_info, 0, _RichCtor(parent=class_decl), {}
    )
    assert writer.class_py_name == "Foo_2"
    assert writer.template_params == ["DIM"]
    assert writer.template_args == ["2"]


def test_init_falls_back_to_decl_name_when_py_name_none():
    class_decl = _RichClassDecl(name="Foo")
    class_info = SimpleNamespace(
        decls=[class_decl],
        py_names=[None],
        template_params=None,
        template_arg_lists=None,
    )
    writer = CppConstructorWrapperWriter(
        class_info, 0, _RichCtor(parent=class_decl), {}
    )
    assert writer.class_py_name == "Foo"
    assert writer.template_args is None


def _exclude_writer(monkeypatch, class_decl, ctor, class_info=None):
    _no_copy_ctor(monkeypatch)
    writer = object.__new__(CppConstructorWrapperWriter)
    writer.class_decl = class_decl
    writer.ctor_decl = ctor
    writer.class_info = class_info or _ClassInfo()
    return writer


def test_exclude_private_pure_virtual(monkeypatch):
    class_decl = _RichClassDecl(
        member_fns=[_MemberFn(virtuality="pure virtual", access_type="private")]
    )
    ctor = _RichCtor(parent=class_decl)
    assert _exclude_writer(monkeypatch, class_decl, ctor).exclude() is True


def test_exclude_abstract_with_abstract_base(monkeypatch):
    abstract_base = _RichClassDecl(name="Base", is_abstract=True)
    class_decl = _RichClassDecl(
        is_abstract=True, recursive_bases=[SimpleNamespace(related_class=abstract_base)]
    )
    ctor = _RichCtor(parent=class_decl)
    assert _exclude_writer(monkeypatch, class_decl, ctor).exclude() is True


def test_exclude_subclass_constructor(monkeypatch):
    class_decl = _RichClassDecl()
    other_parent = _RichClassDecl(name="Inner")
    ctor = _RichCtor(parent=other_parent)  # parent != class_decl
    assert _exclude_writer(monkeypatch, class_decl, ctor).exclude() is True


def test_exclude_artificial_copy_constructor(monkeypatch):
    monkeypatch.setattr(
        exclusions_module.type_traits_classes,
        "is_copy_constructor",
        lambda decl: True,
    )
    class_decl = _RichClassDecl()
    ctor = _RichCtor(parent=class_decl, is_artificial=True)
    writer = object.__new__(CppConstructorWrapperWriter)
    writer.class_decl = class_decl
    writer.ctor_decl = ctor
    writer.class_info = _ClassInfo()
    assert writer.exclude() is True


def test_exclude_iterator_argument(monkeypatch):
    class_decl = _RichClassDecl()
    ctor = _RichCtor(arg_types=["FooIterator const &"], parent=class_decl)
    assert _exclude_writer(monkeypatch, class_decl, ctor).exclude() is True


def test_exclude_by_arg_type(monkeypatch):
    class_decl = _RichClassDecl()
    ctor = _RichCtor(arg_types=["::Node<2> const &"], parent=class_decl)
    class_info = _ClassInfo()
    class_info.hierarchy_attribute_gather = lambda name: (
        [["Node"]] if name == "arg_type_excludes" else []
    )
    assert _exclude_writer(monkeypatch, class_decl, ctor, class_info).exclude() is True


def _gen_writer(
    monkeypatch,
    ctor,
    template_params=None,
    template_args=None,
    exclude_default_args=False,
):
    _no_copy_ctor(monkeypatch)
    class_decl = _RichClassDecl(name="Foo")
    ctor.parent = class_decl
    writer = object.__new__(CppConstructorWrapperWriter)
    writer.class_decl = class_decl
    writer.ctor_decl = ctor
    writer.template_params = template_params
    writer.template_args = template_args
    writer.wrapper_templates = {
        "class_constructor": Template("py::init<$arg_signature>()$default_args")
    }
    info = _ClassInfo()
    info.name = "Foo"
    info.hierarchy_attribute = lambda name: (
        exclude_default_args if name == "exclude_default_args" else None
    )
    writer.class_info = info
    return writer


def test_generate_wrapper_with_default_value(monkeypatch):
    ctor = _RichCtor(
        arg_types=["int"],
        arguments=[_Arg("count", default_value="(-1)", decl_type="int")],
    )
    result = _gen_writer(monkeypatch, ctor).generate_wrapper()
    assert result == 'py::init<int>(), py::arg("count") = -1'


def test_generate_wrapper_excluded_returns_empty(monkeypatch):
    ctor = _RichCtor(arg_types=["FooIterator"], arguments=[])
    assert _gen_writer(monkeypatch, ctor).generate_wrapper() == ""


def test_generate_wrapper_substitutes_template_param(monkeypatch):
    ctor = _RichCtor(
        arg_types=["unsigned"],
        arguments=[_Arg("dim", default_value="DIM", decl_type="unsigned")],
    )
    writer = _gen_writer(
        monkeypatch, ctor, template_params=["DIM"], template_args=["2"]
    )
    assert writer.generate_wrapper() == 'py::init<unsigned>(), py::arg("dim") = 2'


def test_generate_wrapper_empty_initializer_list(monkeypatch):
    monkeypatch.setattr(
        type_traits,
        "remove_const",
        lambda decl_type: SimpleNamespace(decl_string="std::vector<int>"),
    )
    ctor = _RichCtor(
        arg_types=["std::vector<int>"],
        arguments=[_Arg("items", default_value="{}", decl_type="std::vector<int>")],
    )
    result = _gen_writer(monkeypatch, ctor).generate_wrapper()
    assert 'py::arg("items") = std::vector<int> {}' in result
