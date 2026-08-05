#ifndef MACRO_MESH_HPP_
#define MACRO_MESH_HPP_

/**
 * A minimal templated class whose explicit template instantiations are declared
 * via a macro (see MacroMesh.cpp). cppwg's source-text scan does not expand
 * macros, so the instantiations are discovered via the pygccxml fallback.
 *
 * SPACE_DIM has a default argument, so recovering the full instantiation
 * arguments through the fallback requires CastXML >= 0.6.0 (older versions drop
 * a defaulted trailing template argument from the instantiation name).
 */
template <unsigned ELEMENT_DIM, unsigned SPACE_DIM = ELEMENT_DIM>
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

#endif // MACRO_MESH_HPP_
