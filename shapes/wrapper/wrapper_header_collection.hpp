#ifndef pyshapes_HEADERS_HPP_
#define pyshapes_HEADERS_HPP_

// Includes
#include "Shape.hpp"
#include "Rectangle.hpp"
#include "Cuboid.hpp"
#include "Point.hpp"
#include "SimpleMathFunctions.hpp"

// Instantiate Template Classes 
template class Point<2>;
template class Point<3>;
template class Shape<2>;
template class Shape<3>;

// Typedef for nicer naming
namespace cppwg{ 
typedef Point<2> Point2;
typedef Point<3> Point3;
typedef Shape<2> Shape2;
typedef Shape<3> Shape3;
}

#endif // pyshapes_HEADERS_HPP_
