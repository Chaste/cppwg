#ifndef _SHAPE_HPP
#define _SHAPE_HPP

#include <vector>
#include <memory>
#include "Point.hpp"

/**
 * A DIM dimensional shape
 */
template<unsigned DIM>
class Shape
{
protected:

    /**
     * The shape index
     */
    unsigned mIndex;

    /**
     * The shape vertices
     */
    std::vector<std::shared_ptr<Point<DIM> > > mVertices;

public:

    /**
     * Default Constructor
     */
    Shape();

    /**
     * Destructor
     */
    ~Shape();

    /**
     * Return the shape index
     */
    unsigned GetIndex() const;

    /**
     * Return the shape vertices
     */
    const std::vector<std::shared_ptr<Point<DIM> > >& rGetVertices() const;

    /**
     * Set the shape index
     */
    void SetIndex(unsigned index);

    /**
     * Set the shape vertices
     */
     void SetVertices(const std::vector<std::shared_ptr<Point<DIM> > >& rVertices);
};


#endif  // _SHAPE_HPP
