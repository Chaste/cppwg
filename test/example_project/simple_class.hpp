#ifndef _SIMPLE_CLASS_HPP
#define _SIMPLE_CLASS_HPP

#include <string>

class Pet
{
private:

    std::string mName;

public:

    Pet(const std::string& rName = "Dave");

    ~Pet();

    void SetName(const std::string& rName);

    const std::string& rGetName() const;
};

class Dog : public Pet
{
public:

    Dog(const std::string& rName = "Patch");

    std::string Bark() const;
};



#endif  // _SIMPLE_CLASS_HPP
