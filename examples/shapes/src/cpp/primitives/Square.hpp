#ifndef SQUARE_HPP_
#define SQUARE_HPP_

#include "Rectangle.hpp"

/**
 * A Square
 */
class Square : public Rectangle
{

public:
    /**
     * Default Constructor
     */
    Square(double width = 2.0);

    /**
     * Destructor
     */
    ~Square();
};

#endif // SQUARE_HPP_
