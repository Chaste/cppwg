"""
This file contains a list of classes that are to be wrapped.

Each class includes metadata such as template arguments, excluded methods,
methods with special pointer management requirements, and any special
declaration code needed for wrapping. A minimal case is just to
specify the class name and component it will belong to.
"""

import os
import fnmatch
try:
    import cPickle as pickle
except:
    import pickle


class CppClassInfo():

    """
    A container for each class to be wrapped. Include the class name,
    template arguments and specify if any custom code is needed to
    complete the wrapping.

    Template arguments are specified in a list of lists. For example if a
    class is templated over a single dimension <DIM> then the template
    list might look like [[2], [3]]. If templated over two dimensions <ELEMENT, DIM>
    <SPACE, DIM> it might look like [[2,2], [3,3]]. If templated over type it might look
    like [[UniformCellCycleModel, 2], [SimpleOxygenBasedCellCycleModel, 2]]

    :param: name - the class name, for example AbstractCellPopulation
    :param: component - which module the class will be in, e.g. ode, pde, core, cell_based
    :param: template_args - a list of lists containing the template arguments
    :param: skip_wrapping - do not wrap the class if True. The class can still go in include files
    :param: excluded_methods - a list of methods not to be wrapped
    :param: excluded_variables - a list of public member variables not to be wrapped
    :param: pointer_return_methods - a list of lists of methods with special pointer
    or reference return requirements and the name of the Py++ method for managing them.
    :param: needs_include_file - should the class be added to the include file, mostly yes
    :param: include_file_only - should the class only be added to the include file and nothing else
    :param: declaration_code - a list of extra Boost Python wrapper codes to be added to the autowrapper
    :param: needs_instantiation - does the class need instantiation in the header, mostly True for templated
    classes
    """

    def __init__(self, name, component=None, template_args=None,
                 skip_wrapping=False,
                 excluded_methods=None, excluded_variables=None,
                 pointer_return_methods=None,
                 needs_include_file=True, include_file_only=False,
                 declaration_code=None,
                 needs_instantiation=True, name_override=None,
                 include_vec_ptr_self=False,
                 include_ptr_self=False, include_raw_ptr_self=False,
                 constructor_arg_type_excludes=None):

        self.name = name
        self.component = component
        self.template_args = template_args
        self.skip_wrapping = skip_wrapping
        self.excluded_methods = excluded_methods
        self.excluded_variables = excluded_variables
        self.needs_include_file = needs_include_file
        self.pointer_return_methods = pointer_return_methods
        self.include_file_only = include_file_only
        self.declaration_code = declaration_code
        self.needs_instantiation = needs_instantiation
        self.full_path = None
        self.name_override = name_override
        self.include_vec_ptr_self = include_vec_ptr_self
        self.include_ptr_self = include_ptr_self
        self.include_raw_ptr_self = include_raw_ptr_self
        self.include_in_this_module = True
        if constructor_arg_type_excludes is None:
            self.constructor_arg_type_excludes = []
        else:
            self.constructor_arg_type_excludes = constructor_arg_type_excludes
        self.name_replacements = {"double": "Double",
                                  "unsigned int": "Unsigned",
                                  "Unsigned int": "Unsigned",
                                  "unsigned": "Unsigned",
                                  "double": "Double",
                                  "std::vector": "Vector",
                                  "std::pair": "Pair",
                                  "std::map": "Map",
                                  "std::string": "String",
                                  "boost::shared_ptr": "SharedPtr",
                                  "*": "Ptr",
                                  "c_vector": "CVector",
                                  "std::set": "Set"}

    def get_short_names(self):

        """
        Return the name of the class as it will appear on the Python side. This
        collapses template arguements, separating them by underscores and removes
        special characters. The return type is a list, as a class can have multiple
        names if it is templated.
        """

        if self.template_args is None:
            if self.name_override is None:
                return [self.name]
            else:
                return [self.name_override]

        names = []
        for eachTemplateArg in self.template_args:
            template_string = ""
            for idx, eachTemplateEntry in enumerate(eachTemplateArg):

                # Do standard translations
                current_name = str(eachTemplateEntry)
                for eachReplacementString in self.name_replacements.keys():
                    replacement = self.name_replacements[eachReplacementString]
                    current_name = current_name.replace(eachReplacementString,
                                                        replacement)

                cleaned_entry = current_name.translate(None, "<>:,")
                cleaned_entry = cleaned_entry.replace(" ", "")
                if len(cleaned_entry) > 1:
                    first_letter = cleaned_entry[0].capitalize()
                    cleaned_entry = first_letter + cleaned_entry[1:]
                template_string += str(cleaned_entry)
                if(idx != len(eachTemplateArg)-1):
                    template_string += "_"

            current_name = self.name
            if self.name_override is not None:
                current_name = self.name_override

            # Do standard translations
            for eachReplacementString in self.name_replacements.keys():
                replacement = self.name_replacements[eachReplacementString]
                current_name = current_name.replace(eachReplacementString,
                                                    replacement)

            # Strip templates and scopes
            cleaned_name = current_name.translate(None, "<>:,")
            cleaned_name = cleaned_name.replace(" ", "")
            if len(cleaned_name) > 1:
                cleaned_name = cleaned_name[0].capitalize()+cleaned_name[1:]
            names.append(cleaned_name+template_string)
        return names

    def get_full_names(self):

        """
        Return the name (declaration) of the class as it appears on the C++ side.
        The return type is a list, as a class can have multiple
        names (declarations) if it is templated.
        """

        if self.template_args is None:
            return [self.name]

        names = []
        for eachTemplateArg in self.template_args:
            template_string = "<"
            for idx, eachTemplateEntry in enumerate(eachTemplateArg):
                template_string += str(eachTemplateEntry)
                if(idx == len(eachTemplateArg)-1):
                    template_string += " >"
                else:
                    template_string += ","
            names.append(self.name + template_string)
        return names

    def needs_header_file_instantiation(self):

        """
        Does this class need to be instantiated in the header file
        """

        return ((self.template_args is not None) and
                (not self.include_file_only) and
                (self.needs_instantiation))

    def needs_header_file_typdef(self):

        """
        Does this class need to be typdef'd with a nicer name in the header
        file. All template classes need this.
        """

        cond1 = (self.template_args is not None) and (not
                                                      self.include_file_only)
        cond2 = (self.include_vec_ptr_self or self.include_ptr_self or
                 self.include_raw_ptr_self)

        return cond1 or cond2

    def needs_auto_wrapper_generation(self):

        """
        Does this class need a wrapper to be autogenerated.
        """

        return (not self.include_file_only) and (not self.skip_wrapping)