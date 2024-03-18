from typing import Dict, Optional

from pygccxml import declarations
from pygccxml.declarations.class_declaration import class_t
from pygccxml.declarations.calldef_members import constructor_t

from cppwg.input.class_info import CppClassInfo
from cppwg.writers.base_writer import CppBaseWrapperWriter


class CppConstructorWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of constructor wrapper code

    Attributes
    ----------
    class_info : ClassInfo
        The class information for the class containing the constructor
    ctor_decl : constructor_t
        The pygccxml declaration object for the constructor
    class_decl : class_t
        The class declaration for the class containing the constructor
    wrapper_templates : Dict[str, str]
        String templates with placeholders for generating wrapper code
    class_short_name : Optional[str]
        The short name of the class e.g. 'Foo2_2'
    """

    def __init__(
        self,
        class_info: CppClassInfo,
        ctor_decl: constructor_t,
        class_decl: class_t,
        wrapper_templates: Dict[str, str],
        class_short_name: Optional[str] = None,
    ):

        super(CppConstructorWrapperWriter, self).__init__(wrapper_templates)

        self.class_info: CppClassInfo = class_info
        self.ctor_decl: constructor_t = ctor_decl
        self.class_decl: class_t = class_decl

        self.class_short_name = class_short_name
        if self.class_short_name is None:
            self.class_short_name = self.class_decl.name

    def exclusion_criteria(self) -> bool:
        """
        Check if the constructor should be excluded from the wrapper code

        Returns
        -------
        bool
            True if the constructor should be excluded, False otherwise
        """

        # Exclude constructors for classes with private pure virtual methods
        if any(
            mf.virtuality == "pure virtual" and mf.access_type == "private"
            for mf in self.class_decl.member_functions(allow_empty=True)
        ):
            return True

        # Exclude constructors for abstract classes inheriting from abstract bases
        if self.class_decl.is_abstract and len(self.class_decl.recursive_bases) > 0:
            if any(
                base.related_class.is_abstract
                for base in self.class_decl.recursive_bases
            ):
                return True

        # Exclude sub class (e.g. iterator) constructors such as:
        #   class Foo {
        #     public:
        #       class FooIterator {
        if self.ctor_decl.parent != self.class_decl:
            return True

        # Exclude default copy constructors e.g. Foo::Foo(Foo const & foo)
        if (
            declarations.is_copy_constructor(self.ctor_decl)
            and self.ctor_decl.is_artificial
        ):
            return True

        # Check for excluded argument patterns
        calldef_excludes = [
            x.replace(" ", "")
            for x in self.class_info.hierarchy_attribute_gather("calldef_excludes")
        ]

        ctor_arg_type_excludes = [
            x.replace(" ", "")
            for x in self.class_info.hierarchy_attribute_gather(
                "constructor_arg_type_excludes"
            )
        ]

        for arg_type in self.ctor_decl.argument_types:
            # e.g. ::std::vector<unsigned int> const & -> ::std::vector<unsignedint>const&
            arg_type_str = arg_type.decl_string.replace(" ", "")

            # Exclude constructors with "iterator" in args
            if "iterator" in arg_type_str.lower():
                return True

            # Exclude constructors with args matching calldef_excludes
            if arg_type_str in calldef_excludes:
                return True

            # Exclude constructurs with args matching constructor_arg_type_excludes
            for excluded_type in ctor_arg_type_excludes:
                if excluded_type in arg_type_str:
                    return True

        return False

    def add_self(self, cpp_string: str) -> str:
        """
        Add the constructor wrapper code to the input string for example:
        .def(py::init<int, bool >(), py::arg("i") = 1, py::arg("b") = false)

        Parameters
        ----------
        cpp_string : str
            The input string containing current wrapper code

        Returns
        -------
        str
            The input string with the constructor wrapper code added
        """

        # Skip excluded constructors
        if self.exclusion_criteria():
            return cpp_string

        # Get the arg signature e.g. "int, bool"
        cpp_string += "        .def(py::init<"

        arg_types = [t.decl_string for t in self.ctor_decl.argument_types]
        cpp_string += ", ".join(arg_types)

        cpp_string += " >()"
        
        # Default args e.g. py::arg("i") = 1
        default_args = ""
        if not self.default_arg_exclusion_criteria():
            for arg in self.ctor_decl.arguments:
                default_args += f', py::arg("{arg.name}")'

                if arg.default_value is not None:
                    # TODO: Fix <DIM> in default args (see method_writer)
                    default_args += f" = {arg.default_value}"

        cpp_string += default_args + ")\n"

        return cpp_string
