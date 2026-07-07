#ifndef MACROMESH_HPP_
#define MACROMESH_HPP_

/**
 * A minimal templated class whose explicit template instantiations are declared
 * via a macro (see MacroMesh.cpp). cppwg's source-text scan does not expand
 * macros, so the instantiations are discovered via the pygccxml fallback.
 */
template <unsigned ELEMENT_DIM, unsigned SPACE_DIM>
class MacroMesh
{
public:
    MacroMesh()
    {
    }

    unsigned GetDimension() const
    {
        return SPACE_DIM;
    }
};

#endif // MACROMESH_HPP_
