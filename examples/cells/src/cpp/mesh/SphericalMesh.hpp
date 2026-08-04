#ifndef SPHERICAL_MESH_HPP_
#define SPHERICAL_MESH_HPP_

#include "AbstractSphericalMesh.hpp"

/**
 * A concrete spherical mesh.
 *
 * It implements the whole AbstractMesh/AbstractSphericalMesh interface, so it is
 * concrete and constructible. Its overrides of Scale (AbstractMesh) and
 * GetNumElements (AbstractSphericalMesh) each redeclare a virtual that its
 * wrapped base already binds; with exclude_inherited_overrides set on the
 * module, cppwg skips these redundant override bindings.
 */
template <unsigned ELEMENT_DIM, unsigned SPACE_DIM = ELEMENT_DIM>
class SphericalMesh : public AbstractSphericalMesh<ELEMENT_DIM, SPACE_DIM>
{
private:
    /**
     * The number of elements in the mesh
     */
    unsigned mNumElements;

public:
    /**
     * Default Constructor
     */
    SphericalMesh()
        : mNumElements(0)
    {
    }

    /**
     * Destructor
     */
    ~SphericalMesh()
    {
    }

    /**
     * Scale the mesh by a factor.
     */
    void Scale(const double factor) override
    {
        (void)factor;
    }

    /**
     * Return the number of elements in the mesh.
     */
    unsigned GetNumElements() const override
    {
        return mNumElements;
    }
};

#endif // SPHERICAL_MESH_HPP_
