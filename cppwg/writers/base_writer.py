from collections import OrderedDict

from pygccxml.declarations import free_function_t


class CppBaseWrapperWriter:
    """
    Base class for wrapper writers

    Attributes
    ----------
    wrapper_templates : dict[str, str]
        String templates with placeholders for generating wrapper code
    tidy_replacements : OrderedDict[str, str]
        A dictionary of replacements to use when tidying up C++ declarations
    """

    def __init__(self, wrapper_templates: dict[str, str]):

        self.wrapper_templates = wrapper_templates
        self.tidy_replacements = OrderedDict(
            [
                (" ", ""),
                (",", "_"),
                ("<", "_lt_"),
                (">", "_gt_"),
                ("::", "_"),
                ("*", "Ptr"),
                ("&", "Ref"),
                ("-", "neg"),
            ]
        )

    def tidy_name(self, name: str) -> str:
        """
        This method replaces full C++ declarations with a simple version for use
        in typedefs

        Example:
        "::foo::bar<double, 2>" -> "_foo_bar_lt_double_2_gt_"

        Parameters
        ----------
        name : str
            The C++ declaration to tidy up

        Returns
        -------
        str
            The tidied up C++ declaration
        """

        for key, value in self.tidy_replacements.items():
            name = name.replace(key, value)

        return name

    # TODO: Consider moving this implementation  of exclusion_criteria to the
    #      free function writer it is only used there. exclusion_criteria is
    #      currently overriden in method writer and constructor writer.
    def exclusion_critera(
        self, decl: free_function_t, exclusion_args: list[str]
    ) -> bool:
        """
        Checks if any of the types in the function declaration appear in the
        exclusion args.

        Parameters
        ----------
        decl : free_function_t
            The declaration of the function or class
        exclusion_args : list[str]
            A list of arguments to exclude from the wrapper code

        Returns
        -------
        bool
            True if the function should be excluded from the wrapper code
        """

        # Are any return types not wrappable
        return_type = decl.return_type.decl_string.replace(" ", "")
        if return_type in exclusion_args:
            return True

        # Are any arguments not wrappable
        for decl_arg_type in decl.argument_types:
            arg_type = decl_arg_type.decl_string.split()[0].replace(" ", "")
            if arg_type in exclusion_args:
                return True

        return False

    # TODO: This method is currently a placeholder. Consider implementing or removing.
    def default_arg_exclusion_criteria(self) -> bool:

        return False
