#include "Shape.hpp"

template<unsigned DIM>
Shape<DIM>::Shape() :
    mIndex(0),
    mVertices()
{

}

template<unsigned DIM>
Shape<DIM>::~Shape()
{

}

template<unsigned DIM>
unsigned Shape<DIM>::GetIndex() const
{
    return mIndex;
}

template<unsigned DIM>
const std::vector<std::shared_ptr<Point<DIM> > >& Shape<DIM>::rGetVertices() const
{
    return mVertices;
}

template<unsigned DIM>
void Shape<DIM>::SetIndex(unsigned index)
{
    mIndex = index;
}

template<unsigned DIM>
void Shape<DIM>::SetVertices(const std::vector<std::shared_ptr<Point<DIM> > >& rVertices)
{
    mVertices = rVertices;
}

template class Shape<2>;
template class Shape<3>;
