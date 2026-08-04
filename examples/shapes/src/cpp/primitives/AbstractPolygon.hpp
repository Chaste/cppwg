#ifndef ABSTRACTPOLYGON_HPP_
#define ABSTRACTPOLYGON_HPP_

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

#endif // ABSTRACTPOLYGON_HPP_
