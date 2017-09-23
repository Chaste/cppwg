#include "simple_class.hpp"

Pet::Pet(const std::string& rName) :
    mName(rName)
{

}

Pet::~Pet()
{

}

void Pet::SetName(const std::string& rName)
{
    mName = rName;
}

const std::string& Pet::rGetName() const
{
    return mName;
}

Dog::Dog(const std::string& rName) :
        Pet(rName)
{

}

std::string Dog::Bark() const
{
    return "Woof";
}
