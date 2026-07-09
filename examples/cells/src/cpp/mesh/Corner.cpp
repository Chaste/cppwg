#include "Corner.hpp"

template <unsigned DIM>
Corner<DIM>::Corner()
{
}

template <unsigned DIM>
Corner<DIM>::~Corner()
{
    // Deliberately does not delete subs (they are owned elsewhere), so a
    // Corner<DIM> destructor never needs Corner<DIM-1>'s destructor.
}

template <unsigned DIM>
unsigned Corner<DIM>::GetNumSubs() const
{
    return mSubs.size();
}

template <unsigned DIM>
Corner<DIM - 1>* Corner<DIM>::GetSub(unsigned index) const
{
    return mSubs[index];
}

template <unsigned DIM>
void Corner<DIM>::AddSub(Corner<DIM - 1>* pSub)
{
    mSubs.push_back(pSub);
}

// Instantiate Corner<1> and Corner<2> - but NOT Corner<0>, exactly as Facet.cpp
// omits Facet<0>. cppwg discovers both and auto-drops Corner<1> (whose GetSub
// returns the never-instantiated Corner<0>), keeping the safe Corner<2>.
template class Corner<1>;
template class Corner<2>;
