from typing import Optional

from pygccxml import declarations
from pygccxml.declarations.class_declaration import class_t
from pygccxml.declarations.calldef_members import member_function_t

from cppwg.input.class_info import CppClassInfo
from cppwg.writers.base_writer import CppBaseWrapperWriter


class CppMethodWrapperWriter(CppBaseWrapperWriter):
    """
    Manage addition of method wrapper code

    Attributes
    ----------
    class_info : ClassInfo
        The class information for the class containing the method
    method_decl : member_function_t
        The pygccxml declaration object for the method
    class_decl : class_t
        The class declaration for the class containing the method
    wrapper_templates : dict[str, str]
        String templates with placeholders for generating wrapper code
    class_short_name : Optional[str]
        The short name of the class e.g. 'Foo2_2'
    """

    def __init__(
        self,
        class_info: CppClassInfo,
        method_decl: member_function_t,
        class_decl: class_t,
        wrapper_templates: dict[str, str],
        class_short_name: Optional[str] = None,
    ):

        super(CppMethodWrapperWriter, self).__init__(wrapper_templates)

        self.class_info: CppClassInfo = class_info
        self.method_decl: member_function_t = method_decl
        self.class_decl: class_t = class_decl

        self.class_short_name: str = class_short_name
        if self.class_short_name is None:
            self.class_short_name = self.class_decl.name

    def exclusion_criteria(self) -> bool:
        """
        Check if the method should be excluded from the wrapper code

        Returns
        -------
        bool
            True if the method should be excluded, False otherwise
        """

        # Exclude private methods without over-rides
        if self.method_decl.access_type == "private":
            return True

        # Exclude sub class (e.g. iterator) methods such as:
        #   class Foo {
        #     public:
        #       class FooIterator {
        if self.method_decl.parent != self.class_decl:
            return True

        # Check for excluded return types
        calldef_excludes = [
            x.replace(" ", "")
            for x in self.class_info.hierarchy_attribute_gather("calldef_excludes")
        ]

        return_type_excludes = [
            x.replace(" ", "")
            for x in self.class_info.hierarchy_attribute_gather("return_type_excludes")
        ]

        return_type = self.method_decl.return_type.decl_string.replace(" ", "")
        if return_type in calldef_excludes or return_type in return_type_excludes:
            return True

        # Check for excluded argument patterns
        for argument_type in self.method_decl.argument_types:
            # e.g. ::std::vector<unsigned int> const & -> ::std::vector<unsigned
            arg_type_short = argument_type.decl_string.split()[0].replace(" ", "")
            if arg_type_short in calldef_excludes:
                return True

            # e.g. ::std::vector<unsigned int> const & -> ::std::vector<unsignedint>const&
            arg_type_full = argument_type.decl_string.replace(" ", "")
            if arg_type_full in calldef_excludes:
                return True

        return False

    def add_self(self, cpp_string):
        """
        Add the method wrapper code to the input string

        Parameters
        ----------
        cpp_string : str
            The input string containing current wrapper code

        Returns
        -------
        str
            The input string with the constructor wrapper code added
        """

        # Skip excluded methods
        if self.exclusion_criteria():
            return cpp_string

        # Pybind11 def type e.g. "_static" for def_static()
        def_adorn = ""
        if self.method_decl.has_static:
            def_adorn += "_static"

        # How to point to class
        if not self.method_decl.has_static:
            self_ptr = self.class_short_name + "::*"
        else:
            self_ptr = "*"

        # Get the arg signature
        arg_signature = ""
        num_arg_types = len(self.method_decl.argument_types)
        for idx, eachArg in enumerate(self.method_decl.argument_types):
            arg_signature += eachArg.decl_string
            if idx < num_arg_types - 1:
                arg_signature += ", "

        # Const-ness
        const_adorn = ""
        if self.method_decl.has_const:
            const_adorn = " const "

        # Default args
        default_args = ""
        if not self.default_arg_exclusion_criteria():
            arg_types = self.method_decl.argument_types
            for idx, eachArg in enumerate(self.method_decl.arguments):
                default_args += ', py::arg("{}")'.format(eachArg.name)
                if eachArg.default_value is not None:

                    # Hack for missing template in default args
                    repl_value = str(eachArg.default_value)
                    if "<DIM>" in repl_value:
                        if "<2>" in str(arg_types[idx]).replace(" ", ""):
                            repl_value = repl_value.replace("<DIM>", "<2>")
                        elif "<3>" in str(arg_types[idx]).replace(" ", ""):
                            repl_value = repl_value.replace("<DIM>", "<3>")
                    default_args += " = " + repl_value

        # Call policy
        pointer_call_policy = self.class_info.hierarchy_attribute("pointer_call_policy")
        reference_call_policy = self.class_info.hierarchy_attribute(
            "reference_call_policy"
        )

        call_policy = ""
        is_ptr = declarations.is_pointer(self.method_decl.return_type)
        if pointer_call_policy is not None and is_ptr:
            call_policy = ", py::return_value_policy::" + pointer_call_policy
        is_ref = declarations.is_reference(self.method_decl.return_type)
        if reference_call_policy is not None and is_ref:
            call_policy = ", py::return_value_policy::" + reference_call_policy

        method_dict = {
            "def_adorn": def_adorn,
            "method_name": self.method_decl.name,
            "return_type": self.method_decl.return_type.decl_string,
            "self_ptr": self_ptr,
            "arg_signature": arg_signature,
            "const_adorn": const_adorn,
            "class_short_name": self.class_short_name,
            "method_docs": '" "',
            "default_args": default_args,
            "call_policy": call_policy,
        }
        template = self.wrapper_templates["class_method"]
        cpp_string += template.format(**method_dict)
        return cpp_string

    def add_override(self, output_string):

        if self.method_decl.access_type == "private":
            return output_string

        arg_string = ""
        num_arg_types = len(self.method_decl.argument_types)
        args = self.method_decl.arguments
        for idx, eachArg in enumerate(self.method_decl.argument_types):
            arg_string += eachArg.decl_string + " " + args[idx].name
            if idx < num_arg_types - 1:
                arg_string += ", "

        const_adorn = ""
        if self.method_decl.has_const:
            const_adorn = " const "

        overload_adorn = ""
        if self.method_decl.virtuality == "pure virtual":
            overload_adorn = "_PURE"

        all_args_string = ""
        for idx, eachArg in enumerate(self.method_decl.argument_types):
            all_args_string += "" * 8 + args[idx].name
            if idx < num_arg_types - 1:
                all_args_string += ", \n"

        return_string = self.method_decl.return_type.decl_string
        override_dict = {
            "return_type": return_string,
            "method_name": self.method_decl.name,
            "arg_string": arg_string,
            "const_adorn": const_adorn,
            "overload_adorn": overload_adorn,
            "tidy_method_name": self.tidy_name(return_string),
            "short_class_name": self.class_short_name,
            "args_string": all_args_string,
        }
        output_string += self.wrapper_templates["method_virtual_override"].format(
            **override_dict
        )
        return output_string
