#ifndef _Rectangle_HPP
#define _Rectangle_HPP

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
     * Destructor
     */
    ~Rectangle();

};

#endif  // _Rectangle_HPP
