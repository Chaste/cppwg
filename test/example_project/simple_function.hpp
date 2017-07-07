#ifndef _SIMPLE_FUNCTION_HPP
#define _SIMPLE_FUNCTION_HPP

#include "units.hpp"

/**
 * Add the two input numbers and return the result
 * @param i the first number
 * @param j the second number
 * @return the sum of the numbers
 */
inline QLength add(QLength i = 1.0_mm, QLength j = 2.0_m)
{
    return i + j;
}

#endif  // _SIMPLE_FUNCITON_HPP
