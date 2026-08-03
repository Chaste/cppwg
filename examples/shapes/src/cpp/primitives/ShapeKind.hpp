#ifndef _SHAPEKIND_HPP
#define _SHAPEKIND_HPP

#include <string>

/**
 * A plain (namespace-scope) enum. cppwg wraps it as a first-class entity via an
 * `enums:` config entry, exposing it in Python as ShapeKind.CIRCLE etc. Being
 * unscoped, its py::enum_ registration ends with .export_values().
 */
enum ShapeKind
{
    CIRCLE,
    SQUARE,
    TRIANGLE
};

/**
 * A scoped enum (enum class) flows through the same wrapping path; the
 * enumerators are exposed as Handedness.LEFT / Handedness.RIGHT.
 */
enum class Handedness
{
    LEFT,
    RIGHT
};

/**
 * A small class exercising an enum used as a defaulted argument.
 *
 * pybind11 materialises a default argument into a Python object when the method
 * is registered, so ShapeKind must already be registered at that point. cppwg
 * registers a module's enums before its class registration calls precisely so
 * this imports cleanly rather than raising "type not registered yet".
 */
class ShapeClassifier
{
public:
    /**
     * Name the given kind of shape, defaulting to a circle.
     */
    std::string Describe(ShapeKind kind = CIRCLE) const
    {
        switch (kind)
        {
            case SQUARE:
                return "square";
            case TRIANGLE:
                return "triangle";
            default:
                return "circle";
        }
    }

    /**
     * Return a fixed handedness, exercising a scoped enum as a return type.
     */
    Handedness GetHandedness() const
    {
        return Handedness::RIGHT;
    }
};

#endif // _SHAPEKIND_HPP
