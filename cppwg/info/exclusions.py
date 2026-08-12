"""Shared "is this member wrapped?" predicates.

The decision to wrap (or skip) a method, constructor or public data member is
needed in two places: the writers, which emit the binding, and
``PackageInfo._iter_wrapped_arg_return_types``, which yields the argument,
return and member *types* that end up in the generated wrapper (for dependency
pruning and auto-includes). Keeping the rule in one place here means the two
cannot drift out of lockstep.

This lives in the info layer, not a writer: ``cppwg/info/`` must not import
``cppwg/writers/`` (the dependency only runs writers -> info). The writers import
these predicates; the info walk calls them directly.
"""

from typing import TYPE_CHECKING

from pygccxml import declarations
from pygccxml.declarations import type_traits_classes

from cppwg.utils import utils

if TYPE_CHECKING:
    from pygccxml.declarations.calldef_members import constructor_t, member_function_t
    from pygccxml.declarations.class_declaration import class_t
    from pygccxml.declarations.variable import variable_t

    from cppwg.info.class_info import CppClassInfo
    from cppwg.info.free_function_info import CppFreeFunctionInfo


def method_is_excluded(
    class_info: "CppClassInfo",
    class_decl: "class_t",
    method_decl: "member_function_t",
) -> bool:
    """
    Return True if a method would be excluded from the wrapper code.

    Parameters
    ----------
    class_info : CppClassInfo
        The info for the class containing the method.
    class_decl : pygccxml.declarations.class_t
        The declaration of the class the method is being wrapped on.
    method_decl : pygccxml.declarations.member_function_t
        The candidate method.

    Returns
    -------
    bool
        True if the method should be excluded, False otherwise.
    """
    # Skip methods marked for exclusion
    if class_info.excluded_methods:
        if method_decl.name in class_info.excluded_methods:
            return True

    # Exclude private methods
    if method_decl.access_type == "private":
        return True

    # Exclude sub class (e.g. iterator) methods such as:
    #   class Foo {
    #     public:
    #       class FooIterator {
    if method_decl.parent != class_decl:
        return True

    # Exclude by return type. return_type_excludes targets return types;
    # the deprecated calldef_excludes applies to both return and arg types.
    calldef_excludes = class_info.hierarchy_attribute_gather_flat("calldef_excludes")
    return_type_excludes = (
        class_info.hierarchy_attribute_gather_flat("return_type_excludes")
        + calldef_excludes
    )

    return_type = method_decl.return_type.decl_string
    if any(
        utils.type_string_matches(return_type, pattern)
        for pattern in return_type_excludes
    ):
        return True

    # Exclude by argument type. arg_type_excludes targets argument types on
    # methods and constructors; the deprecated calldef_excludes applies too.
    arg_type_excludes = (
        class_info.hierarchy_attribute_gather_flat("arg_type_excludes")
        + calldef_excludes
    )
    for argument_type in method_decl.argument_types:
        arg_type = argument_type.decl_string
        if any(
            utils.type_string_matches(arg_type, pattern)
            for pattern in arg_type_excludes
        ):
            return True

    return False


def constructor_is_excluded(
    class_info: "CppClassInfo",
    class_decl: "class_t",
    ctor_decl: "constructor_t",
) -> bool:
    """
    Return True if a constructor would be excluded from the wrapper code.

    Parameters
    ----------
    class_info : CppClassInfo
        The info for the class containing the constructor.
    class_decl : pygccxml.declarations.class_t
        The declaration of the class the constructor is being wrapped on.
    ctor_decl : pygccxml.declarations.constructor_t
        The candidate constructor.

    Returns
    -------
    bool
        True if the constructor should be excluded, False otherwise.
    """
    # Exclude constructors for classes with private pure virtual methods
    if any(
        mf.virtuality == "pure virtual" and mf.access_type == "private"
        for mf in class_decl.member_functions(allow_empty=True)
    ):
        return True

    # Exclude constructors for abstract classes inheriting from abstract bases.
    # A base whose related_class is None could not be resolved by pygccxml;
    # treat it as non-abstract (skip it) rather than dereferencing None.
    if class_decl.is_abstract and len(class_decl.recursive_bases) > 0:
        if any(
            base.related_class is not None and base.related_class.is_abstract
            for base in class_decl.recursive_bases
        ):
            return True

    # Exclude sub class (e.g. iterator) constructors such as:
    #   class Foo {
    #     public:
    #       class FooIterator {
    if ctor_decl.parent != class_decl:
        return True

    # Exclude compiler-added copy constructors e.g. Foo::Foo(Foo const & foo).
    # Test is_artificial first: it is cheap and gates the heavier is_copy_constructor.
    if ctor_decl.is_artificial and type_traits_classes.is_copy_constructor(ctor_decl):
        return True

    # Argument type strings (canonical, as spelled by pygccxml)
    arg_types = [x.decl_string for x in ctor_decl.argument_types]

    # Exclude constructors with "iterator" in args
    for arg_type in arg_types:
        if "iterator" in arg_type.lower():
            return True

    # Exclude by argument type. arg_type_excludes is the general arg-type exclude
    # (methods and constructors); constructor_arg_type_excludes is a
    # constructor-only refinement; the deprecated calldef_excludes applies too.
    # All are matched the same (boundary-aware) way.
    arg_type_excludes = (
        class_info.hierarchy_attribute_gather_flat("arg_type_excludes")
        + class_info.hierarchy_attribute_gather_flat("constructor_arg_type_excludes")
        + class_info.hierarchy_attribute_gather_flat("calldef_excludes")
    )
    for arg_type in arg_types:
        if any(
            utils.type_string_matches(arg_type, pattern)
            for pattern in arg_type_excludes
        ):
            return True

    # Exclude constructors matching a full signature in
    # constructor_signature_excludes: same arity, and each argument type matches
    # its positional pattern.
    ctor_signature_excludes = class_info.hierarchy_attribute_gather_flat(
        "constructor_signature_excludes"
    )
    for exclude_types in ctor_signature_excludes:
        # Each entry must be a sequence of per-argument patterns. Skip a mis-typed
        # scalar (e.g. `constructor_signature_excludes: 5`, or a single string),
        # which would otherwise crash on len() or be iterated character by
        # character.
        if not isinstance(exclude_types, (list, tuple)):
            continue

        if len(exclude_types) != len(arg_types):
            continue

        if all(
            utils.type_string_matches(arg_type, exclude_type)
            for arg_type, exclude_type in zip(arg_types, exclude_types)
        ):
            return True

    return False


def variable_exclusion_reason(
    class_info: "CppClassInfo",
    class_decl: "class_t",
    variable_decl: "variable_t",
) -> "str | None":
    """
    Return why a public data member is excluded, or None if it is wrapped.

    The reason is a short label (e.g. "bitfield", "static") that the member
    writer uses for a debug log; callers that only need a yes/no answer use
    variable_is_excluded.

    Parameters
    ----------
    class_info : CppClassInfo
        The info for the class owning the member.
    class_decl : pygccxml.declarations.class_t
        The declaration of the class the member is being wrapped on.
    variable_decl : pygccxml.declarations.variable_t
        The candidate data member.

    Returns
    -------
    str | None
        A short exclusion-reason label, or None if the member is wrapped.
    """
    # Skip members marked for exclusion in the config.
    excluded_variables = class_info.hierarchy_attribute_gather_flat(
        "excluded_variables"
    )
    if variable_decl.name in excluded_variables:
        return "config-excluded"

    # Skip members belonging to a nested class. The variables() query is
    # recursive, so it also returns fields of nested classes (e.g. an iterator);
    # binding one as &Class::field would name a member the class does not have.
    if variable_decl.parent is not class_decl:
        return "nested-class"

    # A reference member (e.g. `T& field`) cannot be bound: you cannot form a
    # pointer-to-member for a reference, so &Class::field is ill-formed.
    if declarations.is_reference(variable_decl.decl_type):
        return "reference"

    # A bitfield member has no address, so &Class::field is ill-formed and it
    # cannot be bound with def_readwrite/def_readonly.
    if variable_decl.bits is not None:
        return "bitfield"

    # A C-style array member (e.g. `double coords[3]`) cannot be bound: a
    # def_readwrite setter assigns to the member, but C arrays are not assignable,
    # and pybind11 has no type caster for a raw array, so both def_readwrite and
    # def_readonly fail to compile. is_const already sees through the array, so
    # this also covers const arrays bound read-only.
    if declarations.is_array(variable_decl.decl_type):
        return "array"

    # Static data members need def_readwrite_static/def_readonly_static and, for
    # in-class-initialised static const members, an out-of-line definition to take
    # their address. Skip them for now (see issue #116 follow-up).
    if (
        variable_decl.type_qualifiers is not None
        and variable_decl.type_qualifiers.has_static
    ):
        return "static"

    # A mutable member is bound read-write, whose pybind11 setter assigns to the
    # member (obj.*pm = value). If the type is not copy-assignable (e.g.
    # std::unique_ptr, std::atomic, or a class with a deleted operator=) that
    # assignment does not compile, so skip it. A const member is bound read-only
    # (no setter), so it is unaffected.
    if not declarations.is_const(
        variable_decl.decl_type
    ) and not utils.type_is_copy_assignable(variable_decl.decl_type):
        return "non-copy-assignable"

    return None


def variable_is_excluded(
    class_info: "CppClassInfo",
    class_decl: "class_t",
    variable_decl: "variable_t",
) -> bool:
    """
    Return True if a public data member would be excluded from the wrapper code.

    Returns
    -------
    bool
        True if the member should be excluded, False otherwise.
    """
    return variable_exclusion_reason(class_info, class_decl, variable_decl) is not None


def free_function_is_excluded(free_function_info: "CppFreeFunctionInfo") -> bool:
    """
    Return True if a free function would be excluded from the wrapper code.

    A free function is dropped when its return type or any argument type matches
    return_type_excludes / arg_type_excludes (the deprecated calldef_excludes
    applies to both). Shared by CppFreeFunctionWrapperWriter and the package model
    so a function whose binding is never emitted is not recorded as wrapped.

    Returns
    -------
    bool
        True if the function should be excluded, False otherwise.
    """
    decl = free_function_info.decls[0]

    # Exclude by return type. return_type_excludes targets return types; the
    # deprecated calldef_excludes applies to both return and arg types.
    calldef_excludes = free_function_info.hierarchy_attribute_gather_flat(
        "calldef_excludes"
    )
    return_type_excludes = (
        free_function_info.hierarchy_attribute_gather_flat("return_type_excludes")
        + calldef_excludes
    )
    return_type = decl.return_type.decl_string
    if any(
        utils.type_string_matches(return_type, pattern)
        for pattern in return_type_excludes
    ):
        return True

    # Exclude by argument type. arg_type_excludes is the general arg-type exclude;
    # the deprecated calldef_excludes applies too.
    arg_type_excludes = (
        free_function_info.hierarchy_attribute_gather_flat("arg_type_excludes")
        + calldef_excludes
    )
    for argument_type in decl.argument_types:
        arg_type = argument_type.decl_string
        if any(
            utils.type_string_matches(arg_type, pattern)
            for pattern in arg_type_excludes
        ):
            return True

    return False
