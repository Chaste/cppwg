#ifndef _POINT_HPP
#define _POINT_HPP

#include <array>

/**
 * A point in DIM dimensional space
 */
template<unsigned DIM>
class Point
{
private:

    /**
     * Point index
     */
    unsigned mIndex;

    /**
     * Point location
     */
    std::array<double, DIM> mLocation;

public:

    /**
     * Default Constructor
     */
    Point();

    /**
     * Constructor
     */
    Point(double x, double y, double z=0.0);

    /**
     * Destructor
     */
    ~Point();

    /**
     * Return the modifiable location
     */
    std::array<double, DIM> GetLocation() const;

    /**
     * Return the const location
     */
    const std::array<double, DIM>& rGetLocation() const;

    /**
     * Return the index
     */
    unsigned GetIndex() const;

    /**
     * Set the index
     */
    void SetIndex(unsigned index);

    /**
     * Set the location
     */
    void SetLocation(const std::array<double, DIM>& rLocation);
};

#endif  // _POINT_HPP
