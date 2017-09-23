#ifndef _SHAPE_HPP
#define _SHAPE_HPP

template<unsigned DIM>
class Shape
{
private:

    unsigned mIndex;

public:

    Shape();

    ~Shape();

    void SetIndex(unsigned index);

    unsigned GetIndex() const;
};
};



#endif  // _SHAPE_HPP
