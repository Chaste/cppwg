#ifndef _POINT_HPP
#define _POINT_HPP

#include <array>

template<unsigned DIM>
class Point
{
private:

    unsigned mIndex;

    std::array<double, DIM> mLocation;

public:

    Point();

    Point(const std::array<double, DIM>& rLocation);

    ~Point();

    std::array<double, DIM> GetLocation() const;

    const std::array<double, DIM>& rGetLocation() const;

    unsigned GetIndex() const;

    void SetIndex(unsigned index);

    void SetLocation(const std::array<double, DIM>& rLocation);
};

#endif  // _POINT_HPP
