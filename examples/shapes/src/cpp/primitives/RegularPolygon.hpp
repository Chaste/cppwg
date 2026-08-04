#ifndef REGULARPOLYGON_HPP_
#define REGULARPOLYGON_HPP_

#include <vector>

#include "AbstractPolygon.hpp"

/**
 * A concrete regular polygon.
 *
 * It implements the whole AbstractShape/AbstractPolygon interface, so it is
 * concrete and constructible. Each override redeclares a virtual that its
 * abstract base already wraps; with exclude_inherited_overrides set on the
 * primitives module, cppwg skips these redundant override bindings.
 */
template <unsigned DIM>
class RegularPolygon : public AbstractPolygon<DIM>
{
protected:
    /**
     * The number of sides
     */
    unsigned mNumSides;

    /**
     * The length of each side
     */
    double mSideLength;

public:
    /**
     * Default Constructor
     */
    RegularPolygon(unsigned numSides = 4, double sideLength = 1.0)
        : mNumSides(numSides),
          mSideLength(sideLength)
    {
    }

    /**
     * Destructor
     */
    ~RegularPolygon()
    {
    }

    /**
     * Return the area of the polygon.
     */
    double GetArea() const override
    {
        return 0.25 * mNumSides * mSideLength * mSideLength;
    }

    /**
     * Return the axis-aligned bounding box.
     */
    std::vector<double> GetBoundingBox() const override
    {
        return std::vector<double>(2 * DIM, mSideLength);
    }

    /**
     * Return the number of sides.
     */
    unsigned GetNumSides() const override
    {
        return mNumSides;
    }
};

#endif // REGULARPOLYGON_HPP_
