#ifndef MESH_FACTORY_HPP_
#define MESH_FACTORY_HPP_

#include <memory>

/**
 * A concrete mesh implementation
 */
template <class MESH>
class MeshFactory
{
public:
    /**
     * Default Constructor
     */
    MeshFactory();

    /**
     * Destructor
     */
    ~MeshFactory();

    /**
     * Generate a mesh
     */
    std::shared_ptr<MESH> generateMesh();
};

#endif // MESH_FACTORY_HPP_
