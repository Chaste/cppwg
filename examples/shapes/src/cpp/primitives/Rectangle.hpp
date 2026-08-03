#ifndef RECTANGLE_HPP_
#define RECTANGLE_HPP_

#include "Point.hpp"
#include "Shape.hpp"

/**
 * A Rectangle
 */
class Rectangle : public Shape<2>
{

public:
    /**
     * Default Constructor
     */
    Rectangle(double width = 2.0, double height = 1.0);

    /**
     * Construct from points
     */
    Rectangle(const std::vector<std::shared_ptr<Point<2> > > points = {});

    /**
     * Destructor
     */
    ~Rectangle();
};

#endif // RECTANGLE_HPP_
