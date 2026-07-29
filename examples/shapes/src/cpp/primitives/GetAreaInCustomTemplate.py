import cppwg.templates.custom


class GetAreaInCustomTemplate(cppwg.templates.custom.Custom):
    """Emit a GetAreaIn<UNIT> binding per area unit.

    cppwg cannot instantiate a templated method, so - as pychaste does for
    AbstractCellPopulation::AddCellWriter<Writer> - the units are listed here and
    one .def is generated per unit. The pyshapes package then exposes them as
    UnitSquare.GetAreaIn[SquareMetres]() via the TemplateMethod descriptor.
    """

    units = ["SquareMetres", "SquareFeet"]

    def get_class_cpp_def_code(self, class_name):
        # Underscore between the base and the unit (GetAreaIn_SquareMetres),
        # matching cppwg's Foo_2 naming so the TemplateMethod descriptor exposes
        # it as GetAreaIn[SquareMetres]().
        template = '        .def("GetAreaIn_{unit}", &{class_name}::GetAreaIn<{unit}>)\n'
        return "".join(
            template.format(class_name=class_name, unit=unit) for unit in self.units
        )

    def get_class_cpp_source_includes(self, *args, **kwargs):
        # The units appear only inside the generated code above, so cppwg cannot
        # infer this header from the parsed signatures.
        return ["AreaUnits.hpp"]
