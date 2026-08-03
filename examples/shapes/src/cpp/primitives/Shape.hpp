#ifndef SHAPE_HPP_
#define SHAPE_HPP_

#include <vector>
#include <memory>
#include "Point.hpp"

/**
 * A DIM dimensional shape
 */
template <unsigned DIM>
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
    std::vector<std::shared_ptr<Point<DIM>>> mVertices;

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
    const std::vector<std::shared_ptr<Point<DIM>>> &rGetVertices() const;

    /**
     * Set the shape index
     */
    void SetIndex(unsigned index);

    /**
     * Set the shape vertices
     */
    void SetVertices(const std::vector<std::shared_ptr<Point<DIM>>> &rVertices);

    /**
     * Add a single vertex to the shape
     */
    void AddVertex(std::shared_ptr<Point<DIM>> point = std::make_shared<Point<DIM>>());
};

#endif // SHAPE_HPP_
