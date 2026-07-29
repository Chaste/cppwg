#ifndef _ABSTRACTPOLYGON_HPP
#define _ABSTRACTPOLYGON_HPP

#include "AbstractShape.hpp"

/**
 * An abstract polygon.
 *
 * This class has an abstract base (AbstractShape) and is itself still abstract:
 * it adds the side-count interface but does not implement the inherited
 * GetArea/GetBoundingBox, so it cannot be instantiated. cppwg therefore wraps
 * it without any constructors.
 */
template <unsigned DIM>
class AbstractPolygon : public AbstractShape<DIM>
{
public:
    /**
     * Return the number of sides of the polygon.
     */
    virtual unsigned GetNumSides() const = 0;
};

#endif // _ABSTRACTPOLYGON_HPP
