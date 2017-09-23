#ifndef _Cuboid_HPP
#define _Cuboid_HPP

#include "Shape.hpp"

/**
 * A Cuboid
 */
class Cuboid : public Shape<3>
{

public:

    /**
     * Default Constructor
     */
    Cuboid(double width = 2.0, double height = 1.0, double depth = 1.0);

    /**
     * Destructor
     */
    ~Cuboid();

};

#endif  // _Cuboid_HPP
