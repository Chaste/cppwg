#ifndef _AREAUNITS_HPP
#define _AREAUNITS_HPP

/**
 * Area-unit policy types, used as template arguments to
 * UnitSquare::GetAreaIn<UNIT>(). Each reports how many of itself make up one
 * square metre.
 */
class SquareMetres
{
public:
    double PerSquareMetre() const
    {
        return 1.0;
    }
};

class SquareFeet
{
public:
    double PerSquareMetre() const
    {
        return 10.7639104;
    }
};

#endif // _AREAUNITS_HPP
