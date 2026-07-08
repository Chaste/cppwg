#ifndef CORNER_HPP_
#define CORNER_HPP_

#include <vector>

/**
 * A minimal templated boundary element - structurally identical to Facet, but
 * left for cppwg to resolve automatically rather than curated by hand.
 *
 * Like Facet, a Corner<DIM> references its lower-dimensional sub-corners
 * (Corner<DIM-1>) only through pointers, is polymorphic (a virtual destructor),
 * and never instantiates the DIM=0 base case Corner<0> (see Corner.cpp). So
 * wrapping the low-dim Corner<1> - whose GetSub returns the never-instantiated
 * Corner<0> - would produce an "undefined symbol: Corner<0>::~Corner" at import.
 *
 * The difference from Facet is purely in the config: Facet is curated to <2>
 * with a template_substitutions block, whereas Corner opts into discovery with
 * no substitutions. cppwg discovers Corner<1> and Corner<2>, then automatically
 * drops Corner<1> (with a warning) because its wrapped interface depends on the
 * uninstantiated Corner<0>, leaving the safe Corner<2> wrapped. This is the
 * non-curated counterpart to Facet's hand-written curation.
 */
template <unsigned DIM>
class Corner
{
    std::vector<Corner<DIM - 1>*> mSubs;

public:
    Corner();
    virtual ~Corner();

    virtual unsigned GetNumSubs() const;
    Corner<DIM - 1>* GetSub(unsigned index) const;
    void AddSub(Corner<DIM - 1>* pSub);
};

#endif // CORNER_HPP_
