#include "Facet.hpp"

// Out-of-line members are emitted only for the explicitly instantiated
// dimensions below. Facet<0> is never instantiated, so its members (e.g. its
// destructor) are never defined - which is fine in C++ because Facet<0> is
// only ever used through pointers.

template <unsigned DIM>
Facet<DIM>::Facet()
{
}

template <unsigned DIM>
Facet<DIM>::~Facet()
{
    // Deliberately does not delete faces (they are owned elsewhere), so a
    // Facet<DIM> destructor never needs Facet<DIM-1>'s destructor.
}

template <unsigned DIM>
Facet<DIM - 1>* Facet<DIM>::GetFace(unsigned index) const
{
    return mFaces[index];
}

template <unsigned DIM>
void Facet<DIM>::AddFace(Facet<DIM - 1>* pFace)
{
    mFaces.push_back(pFace);
}

template <unsigned DIM>
unsigned Facet<DIM>::GetNumFaces() const
{
    return mFaces.size();
}

// Instantiate Facet<1> and Facet<2> - but NOT Facet<0>. (Facet<2>'s faces are
// Facet<1>, which is instantiated; Facet<1>'s faces are Facet<0>, which is not.)
template class Facet<1>;
template class Facet<2>;
