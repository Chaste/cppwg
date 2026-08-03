#ifndef ABSTRACT_SPHERICAL_MESH_HPP_
#define ABSTRACT_SPHERICAL_MESH_HPP_

#include "AbstractMesh.hpp"

/**
 * An abstract spherical mesh.
 *
 * It has an abstract base (AbstractMesh) and is itself still abstract: it adds
 * the element-count interface but does not implement the inherited pure-virtual
 * Scale, so it cannot be instantiated. cppwg therefore wraps it without any
 * constructors.
 */
template <unsigned ELEMENT_DIM, unsigned SPACE_DIM = ELEMENT_DIM>
class AbstractSphericalMesh : public AbstractMesh<ELEMENT_DIM, SPACE_DIM>
{
public:
    /**
     * Return the number of elements in the mesh.
     */
    virtual unsigned GetNumElements() const = 0;
};

#endif // ABSTRACT_SPHERICAL_MESH_HPP_
