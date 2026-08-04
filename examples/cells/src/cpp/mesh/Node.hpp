#ifndef NODE_HPP_
#define NODE_HPP_

#include <boost/numeric/ublas/vector.hpp>

#include <array>
#include <vector>

/**
 * A node in a mesh
 */
template <unsigned SPACE_DIM>
class Node
{
private:
    /**
     * Node index
     */
    unsigned mIndex;

    /**
     * Node location
     */
    boost::numeric::ublas::c_vector<double, SPACE_DIM> mLocation;

public:
    /**
     * Default Constructor
     */
    Node();

    /**
     * Constructor with std::vector coordinates
     */
    Node(std::vector<double> coords);

    /**
     * Constructor with c_vector coordinates
     */
    Node(boost::numeric::ublas::c_vector<double, SPACE_DIM> coords);

    /**
     * Destructor
     */
    ~Node();

    /**
     * Return the index
     */
    unsigned GetIndex() const;

    /**
     * Return the location
     */
    boost::numeric::ublas::c_vector<double, SPACE_DIM> GetLocation();

    /**
     * Translate with the given displacement vector
     */
    void Translate(const boost::numeric::ublas::c_vector<double, SPACE_DIM> &rDisplacement);
};

#endif //NODE_HPP_
