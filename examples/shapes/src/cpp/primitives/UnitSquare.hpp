#ifndef _UNITSQUARE_HPP
#define _UNITSQUARE_HPP

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
};

#endif // _UNITSQUARE_HPP
