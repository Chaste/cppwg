#ifndef FACET_HPP_
#define FACET_HPP_

#include <vector>

/**
 * A minimal templated element that references its lower-dimensional faces
 * (Facet<DIM-1>) only through pointers.
 *
 * The DIM=0 base case, Facet<0>, is used only as a pointer type and is never
 * explicitly instantiated (see Facet.cpp), so its out-of-line members are
 * never emitted. This is valid C++: pointer-only use never requires Facet<0>
 * to be a complete/instantiated type.
 *
 * It reproduces the scenario where wrapping the low-dim Facet<1> (whose
 * GetFace returns the never-instantiated Facet<0>) forces pybind11 to require
 * the complete Facet<0> type, producing an undefined symbol (Facet<0>::~Facet)
 * at import - even though the pure C++ links fine. The curated case
 * (wrap Facet<2> only, whose faces Facet<1> are instantiated) works, arranged
 * by template_substitutions.
 *
 * The class is polymorphic (a virtual destructor, like Chaste's element
 * hierarchy). That matters: pybind11's handling of a returned Facet<0>*
 * consults its RTTI/vtable, which references the (virtual, out-of-line)
 * Facet<0> destructor. A non-polymorphic class has no vtable, so nothing would
 * force that reference and the failure would not occur.
 */
template <unsigned DIM>
class Facet
{
    std::vector<Facet<DIM - 1>*> mFaces;

public:
    Facet();
    virtual ~Facet();

    virtual unsigned GetNumFaces() const;
    Facet<DIM - 1>* GetFace(unsigned index) const;
    void AddFace(Facet<DIM - 1>* pFace);
};

#endif // FACET_HPP_
