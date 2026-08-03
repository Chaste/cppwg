#ifndef TRIANGLE_HPP_
#define TRIANGLE_HPP_

#include "Point.hpp"
#include "Shape.hpp"

/**
 * A Triangle
 */
class Triangle : public Shape<2>
{

public:
    /**
     * Default Constructor
     */
    Triangle(const std::vector<std::shared_ptr<Point<2> > > points);

    /**
     * Destructor
     */
    ~Triangle();
};

#endif // TRIANGLE_HPP_
