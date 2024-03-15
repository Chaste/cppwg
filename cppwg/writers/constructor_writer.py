from typing import Optional

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
    wrapper_templates : dict[str, str]
        String templates with placeholders for generating wrapper code
    class_short_name : Optional[str]
        The short name of the class e.g. 'Foo2_2'
    """

    def __init__(
        self,
        class_info: CppClassInfo,
        ctor_decl: constructor_t,
        class_decl: class_t,
        wrapper_templates: dict[str, str],
        class_short_name: Optional[str] = None,
    ):

        super(CppConstructorWrapperWriter, self).__init__(wrapper_templates)

        self.class_info: CppClassInfo = class_info
        self.ctor_decl: constructor_t = ctor_decl
        self.class_decl: class_t = class_decl

        self.class_short_name = class_short_name
        if self.class_short_name is None:
            self.class_short_name = self.class_decl.name

    def exclusion_critera(self) -> bool:
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

        # Check for excluded arg patterns
        calldef_excludes = self.class_info.hierarchy_attribute_gather(
            "calldef_excludes"
        )

        ctor_arg_type_excludes = self.class_info.hierarchy_attribute_gather(
            "constructor_arg_type_excludes"
        )

        for arg_type in self.ctor_decl.argument_types:
            # Exclude constructors with "iterator" args
            if "iterator" in arg_type.decl_string.lower():
                return True

            # Exclude args matching calldef_excludes
            if arg_type.decl_string.replace(" ", "") in calldef_excludes:
                return True

            # Exclude args matching constructor_arg_type_excludes
            for excluded_arg_type in ctor_arg_type_excludes:
                if excluded_arg_type in arg_type.decl_string:
                    return True

        return False

    def add_self(self, cpp_string: str) -> str:
        """
        Add the constructor wrapper code

        Parameters
        ----------
        cpp_string : str
            The current wrapper code

        Returns
        -------
        str
            The wrapper code with the constructor added
        """

        # Skip excluded constructors
        if self.exclusion_critera():
            return cpp_string

        # Add the constructor definition e.g.
        # .def(py::init<int, bool >(), py::arg("i") = 1, py::arg("b") = false)
        cpp_string += "        .def(py::init<"

        arg_types = [t.decl_string for t in self.ctor_decl.argument_types]
        cpp_string += ", ".join(arg_types)

        cpp_string += " >()"

        default_args = ""
        if not self.default_arg_exclusion_criteria():
            for arg in self.ctor_decl.arguments:
                default_args += f', py::arg("{arg.name}")'
                if arg.default_value is not None:
                    default_args += " = " + arg.default_value

        cpp_string += default_args + ")\n"

        return cpp_string
