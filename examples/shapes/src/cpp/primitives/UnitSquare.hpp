#ifndef UNIT_SQUARE_HPP_
#define UNIT_SQUARE_HPP_

#include "AreaUnits.hpp"

/**
 * A square whose area can be reported in a choice of units via a templated
 * method.
 *
 * cppwg cannot instantiate a templated method itself, so a custom generator
 * (GetAreaInCustomTemplate.py) emits one binding per unit -
 * GetAreaIn_SquareMetres, GetAreaIn_SquareFeet. The pyshapes package then exposes
 * them through the TemplateMethod descriptor as GetAreaIn[SquareMetres]() etc.,
 * mirroring pychaste's AddCellWriter[Writer]().
 *
 * GetAreaIn is also overloaded with a plain, non-templated form that takes an
 * explicit units-per-square-metre factor. cppwg wraps that overload normally as
 * GetAreaIn, which the TemplateMethod descriptor would otherwise shadow; the
 * package keeps it reachable by passing it as the descriptor's fallback, so
 * square.GetAreaIn(factor) works alongside square.GetAreaIn[SquareFeet]() -
 * mirroring pychaste's AddCellWriter(writer) plain overload.
 */
class UnitSquare
{
    double mSide;

public:
    /**
     * Default Constructor
     */
    UnitSquare(double side = 1.0)
        : mSide(side)
    {
    }

    /**
     * Return the area in square metres.
     */
    double GetArea() const
    {
        return mSide * mSide;
    }

    /**
     * Return the area expressed in the given unit.
     */
    template <class UNIT>
    double GetAreaIn() const
    {
        return GetArea() * UNIT().PerSquareMetre();
    }

    /**
     * Return the area expressed in a custom unit, given how many of that unit
     * make up one square metre. A plain (non-templated) overload of GetAreaIn.
     */
    double GetAreaIn(double perSquareMetre) const
    {
        return GetArea() * perSquareMetre;
    }
};

#endif // UNIT_SQUARE_HPP_
