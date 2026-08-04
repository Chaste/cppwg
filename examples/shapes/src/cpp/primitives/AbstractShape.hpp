#ifndef ABSTRACTSHAPE_HPP_
#define ABSTRACTSHAPE_HPP_

#include <vector>

/**
 * An abstract DIM-dimensional shape with a measurable size.
 *
 * This is a pure abstract base: it declares the shape interface but leaves
 * every measurement to its subclasses.
 */
template <unsigned DIM>
class AbstractShape
{
public:
    /**
     * Default Constructor
     */
    AbstractShape()
    {
    }

    /**
     * Destructor
     */
    virtual ~AbstractShape()
    {
    }

    /**
     * Return the area of the shape.
     */
    virtual double GetArea() const = 0;

    /**
     * Return the axis-aligned bounding box as [min..., max...].
     *
     * The return type does not depend on DIM, so every instantiation shares
     * the same trampoline return typedef.
     */
    virtual std::vector<double> GetBoundingBox() const = 0;
};

#endif // ABSTRACTSHAPE_HPP_
