#ifndef _THROWING_FUNCTION_HPP
#define _THROWING_FUNCTION_HPP

#include <string>

/**
 * A simple exception type that does NOT derive from std::exception.
 *
 * pybind11 cannot translate this automatically, so without a registered
 * exception translator it would terminate the Python interpreter. It is used
 * to exercise the package's exception_translation_code option.
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

#endif  // _THROWING_FUNCTION_HPP
