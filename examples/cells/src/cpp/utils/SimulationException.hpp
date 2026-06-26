#ifndef SIMULATIONEXCEPTION_HPP_
#define SIMULATIONEXCEPTION_HPP_

#include <sstream>
#include <stdexcept>
#include <string>

/**
 * A simple exception type that derives from std::runtime_error and exposes
 * its message via GetMessage().
 *
 * A pybind11 exception translator (see dynamic/config.yaml) can use
 * GetMessage() to raise a helpful Python error instead of crashing.
 */
class SimulationException : public std::runtime_error
{
public:
    SimulationException(const std::string& rMessage,
                        const std::string& rFilename,
                        unsigned lineNumber)
        : std::runtime_error(rMessage), mShortMessage(rMessage)
    {
        std::stringstream message;
        message << rFilename << ":" << lineNumber << ": " << rMessage;
        mMessage = message.str();
    }

    /** @return the full message, including file and line number. */
    std::string GetMessage() const
    {
        return mMessage;
    }

    /** @return just the text of the message. */
    std::string GetShortMessage() const
    {
        return mShortMessage;
    }

private:
    std::string mMessage; /**< Full message, including file and line number. */
    std::string mShortMessage; /**< Just the text of the message. */
};

#endif // SIMULATIONEXCEPTION_HPP_
