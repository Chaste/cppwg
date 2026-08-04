#ifndef POTTS_MESH_HPP_
#define POTTS_MESH_HPP_

#include "AbstractMesh.hpp"

/**
 * A Potts mesh implementation
 */
template <unsigned DIM>
class PottsMesh : public AbstractMesh<DIM, DIM>
{
public:
    /**
     * Default Constructor
     */
    PottsMesh();

    /**
     * Destructor
     */
    ~PottsMesh();

    /**
     * Scale the mesh by a factor
     */
    void Scale(const double factor) override;
};

#endif // POTTS_MESH_HPP_
