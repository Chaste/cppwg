#ifndef _THROWING_FUNCTION_HPP
#define _THROWING_FUNCTION_HPP

#include <string>

/**
 * A simple exception type that does not derive from std::exception. It is
 * listed under the package's exceptions option, so cppwg generates a translator
 * that surfaces its GetMessage() text as a Python error.
 */
class ShapeException
{
public:
    explicit ShapeException(const std::string& rMessage) : mMessage(rMessage)
    {
    }

    std::string GetMessage() const
    {
        return mMessage;
    }

private:
    std::string mMessage;
};

/**
 * Throw a ShapeException. Used to test that C++ exceptions surface as Python
 * exceptions rather than crashing the interpreter.
 */
inline void throw_exception()
{
    throw ShapeException("C++ exception thrown");
}

/**
 * An exception type that is not listed in the package's exceptions option, so
 * no translator is generated for it.
 */
class UnwrappedException
{
};

/**
 * Throw an UnwrappedException. Used to test that exceptions without a
 * configured translator are not silently ignored.
 */
inline void throw_unwrapped_exception()
{
    throw UnwrappedException();
}

#endif  // _THROWING_FUNCTION_HPP
