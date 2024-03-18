from typing import Any, Dict, List, Optional

from cppwg.input.base_info import BaseInfo

from pygccxml.declarations import declaration_t


class CppTypeInfo(BaseInfo):
    """
    This class holds information for C++ types including classes, free functions etc.

    Attributes
    ----------
    module_info : ModuleInfo
        The module info parent object associated with this type
    source_file : str
        The source file containing the type
    source_file_full_path : str
        The full path to the source file containing the type
    name_override : str
        The name override specified in config e.g. "CustomFoo" -> "Foo"
    template_arg_lists : List[List[Any]]
        List of template replacement arguments for the type e.g. [[2, 2], [3, 3]]
    decl : declaration_t
        The pygccxml declaration associated with this type
    """

    def __init__(self, name: str, type_config: Optional[Dict[str, Any]] = None):

        super(CppTypeInfo, self).__init__(name)

        self.module_info: Optional["ModuleInfo"] = None
        self.source_file_full_path: Optional[str] = None
        self.source_file: Optional[str] = None
        self.name_override: Optional[str] = None
        self.template_arg_lists: Optional[list[List[Any]]] = None
        self.decl: Optional[declaration_t] = None

        if type_config:
            for key, value in type_config.items():
                setattr(self, key, value)

    # TODO: Consider setting short and full names on init as read-only properties
    def get_short_names(self) -> List[str]:
        """
        Return the name of the class as it will appear on the Python side. This
        collapses template arguments, separating them by underscores and removes
        special characters. The return type is a list, as a class can have
        multiple names if it is templated. For example, a class "Foo" with
        template arguments [[2, 2], [3, 3]] will have a short name list
        ["Foo2_2", "Foo3_3"].

        Returns
        -------
        List[str]
            The list of short names
        """

        # Handles untemplated classes
        if self.template_arg_lists is None:
            if self.name_override is None:
                return [self.name]
            return [self.name_override]

        short_names = []

        # Table of special characters for removal
        rm_chars = {"<": None, ">": None, ",": None, " ": None}
        rm_table = str.maketrans(rm_chars)

        # Clean the type name
        type_name = self.name
        if self.name_override is not None:
            type_name = self.name_override

        # Do standard name replacements e.g. "unsigned int" -> "Unsigned"
        for name, replacement in self.name_replacements.items():
            type_name = type_name.replace(name, replacement)

        # Remove special characters
        type_name = type_name.translate(rm_table)

        # Capitalize the first letter e.g. "foo" -> "Foo"
        if len(type_name) > 1:
            type_name = type_name[0].capitalize() + type_name[1:]

        # Create a string of template args separated by "_" e.g. 2_2
        for template_arg_list in self.template_arg_lists:
            # Example template_arg_list : [2, 2]

            template_string = ""
            for idx, arg in enumerate(template_arg_list):

                # Do standard name replacements
                arg_str = str(arg)
                for name, replacement in self.name_replacements.items():
                    arg_str = arg_str.replace(name, replacement)

                # Remove special characters
                arg_str = arg_str.translate(rm_table)

                # Capitalize the first letter
                if len(arg_str) > 1:
                    arg_str = arg_str[0].capitalize() + arg_str[1:]

                # Add "_" between template arguments
                template_string += arg_str
                if idx < len(template_arg_list) - 1:
                    template_string += "_"

            short_names.append(type_name + template_string)

        return short_names

    def get_full_names(self) -> List[str]:
        """
        Return the name (declaration) of the class as it appears on the C++
        side. The return type is a list, as a class can have multiple names
        (declarations) if it is templated. For example, a class "Foo" with
        template arguments [[2, 2], [3, 3]] will have a full name list
        ["Foo<2,2 >", "Foo<3,3 >"].

        Returns
        -------
        List[str]
            The list of full names
        """

        # Handles untemplated classes
        if self.template_arg_lists is None:
            return [self.name]

        full_names = []
        for template_arg_list in self.template_arg_lists:
            # Create template string from arg list e.g. [2, 2] -> "<2,2 >"
            template_string = ",".join([str(arg) for arg in template_arg_list])
            template_string = "<" + template_string + " >"

            # Join full name e.g. "Foo<2,2 >"
            full_names.append(self.name + template_string)

        return full_names

    # TODO: This method is not used, remove it? 
    def needs_header_file_instantiation(self):
        """
        Does this class need to be instantiated in the header file
        """

        return (
            (self.template_arg_lists is not None)
            and (not self.include_file_only)
            and (self.needs_instantiation)
        )

    # TODO: This method is not used, remove it? 
    def needs_header_file_typdef(self):
        """
        Does this type need to be typdef'd with a nicer name in the header
        file. All template classes need this.
        """

        return (self.template_arg_lists is not None) and (not self.include_file_only)

    # TODO: This method is not used, remove it? 
    def needs_auto_wrapper_generation(self):
        """
        Does this class need a wrapper to be autogenerated.
        """

        return not self.include_file_only
