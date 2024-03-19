#include <memory>
#include "Point.hpp"
#include "Rectangle.hpp"

Rectangle::Rectangle(double width, double height) :
    Shape<2>()
{
    this->mVertices.push_back(std::make_shared<Point<2> >(0.0, 0.0));
    this->mVertices.push_back(std::make_shared<Point<2> >(width, 0.0));
    this->mVertices.push_back(std::make_shared<Point<2> >(width, height));
    this->mVertices.push_back(std::make_shared<Point<2> >(0.0, height));
}

Rectangle::~Rectangle()
{

}
