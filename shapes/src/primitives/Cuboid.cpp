#include <memory>
#include "Point.hpp"
#include "Cuboid.hpp"

Cuboid::Cuboid(double width, double height, double depth) :
    Shape<3>()
{
    this->mVertices.push_back(std::make_shared<Point<3> >(0.0, 0.0, 0.0));
    this->mVertices.push_back(std::make_shared<Point<3> >(width, 0.0, 0.0));
    this->mVertices.push_back(std::make_shared<Point<3> >(width, height, 0.0));
    this->mVertices.push_back(std::make_shared<Point<3> >(0.0, height, 0.0));

    this->mVertices.push_back(std::make_shared<Point<3> >(0.0, 0.0, depth));
    this->mVertices.push_back(std::make_shared<Point<3> >(width, 0.0, depth));
    this->mVertices.push_back(std::make_shared<Point<3> >(width, height, depth));
    this->mVertices.push_back(std::make_shared<Point<3> >(0.0, height, depth));
}

Cuboid::~Cuboid()
{

}
