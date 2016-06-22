/***************************************************************************
   Copyright 2015 Ufora Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
****************************************************************************/
#pragma once
#include <ostream>
#include <stdio.h>
#include <sstream>
#include "cppml/CPPMLPrettyPrinter.hppml"

enum LogLevel {
    LOG_LEVEL_DEBUG = 0,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_CRITICAL,
    LOG_LEVEL_TEST
};


#define LOG_LEVEL_SCOPED(scope) \
    ([]() { \
        static LogLevel** shouldLog = \
                Ufora::Logging::getScopedLoggingLevelHandle(scope, __FILE__); \
            return **shouldLog; \
        }())

#define SHOULD_LOG_DEBUG_SCOPED(scope) (LOG_LEVEL_SCOPED(scope) <= LOG_LEVEL_DEBUG)
#define SHOULD_LOG_INFO_SCOPED(scope) (LOG_LEVEL_SCOPED(scope) <= LOG_LEVEL_INFO)
#define SHOULD_LOG_WARN_SCOPED(scope) (LOG_LEVEL_SCOPED(scope) <= LOG_LEVEL_WARN)
#define SHOULD_LOG_ERROR_SCOPED(scope) (LOG_LEVEL_SCOPED(scope) <= LOG_LEVEL_ERROR)
#define SHOULD_LOG_CRITICAL_SCOPED(scope) (LOG_LEVEL_SCOPED(scope) <= LOG_LEVEL_CRITICAL)
#define SHOULD_LOG_TEST_SCOPED(scope) (LOG_LEVEL_SCOPED(scope) <= LOG_LEVEL_TEST)

#define SHOULD_LOG_DEBUG() SHOULD_LOG_DEBUG_SCOPED("")
#define SHOULD_LOG_INFO() SHOULD_LOG_INFO_SCOPED("")
#define SHOULD_LOG_WARN() SHOULD_LOG_WARN_SCOPED("")
#define SHOULD_LOG_ERROR() SHOULD_LOG_ERROR_SCOPED("")
#define SHOULD_LOG_CRITICAL() SHOULD_LOG_CRITICAL_SCOPED("")
#define SHOULD_LOG_TEST() SHOULD_LOG_TEST_SCOPED("")

#define LOG_DEBUG if(!SHOULD_LOG_DEBUG()) ; else (::Ufora::Logging::Logger(LOG_LEVEL_DEBUG, __FILE__, __LINE__))
#define LOG_INFO if(!SHOULD_LOG_INFO()) ; else  ::Ufora::Logging::Logger(LOG_LEVEL_INFO, __FILE__, __LINE__)
#define LOG_WARN if(!SHOULD_LOG_WARN()) ; else  (::Ufora::Logging::Logger(LOG_LEVEL_WARN, __FILE__, __LINE__))
#define LOG_ERROR if(!SHOULD_LOG_ERROR()) ; else  (::Ufora::Logging::Logger(LOG_LEVEL_ERROR, __FILE__, __LINE__))
#define LOG_CRITICAL if(!SHOULD_LOG_CRITICAL()) ; else  (::Ufora::Logging::Logger(LOG_LEVEL_CRITICAL, __FILE__, __LINE__))
#define LOG_TEST if(!SHOULD_LOG_TEST()) ; else  (::Ufora::Logging::Logger(LOG_LEVEL_TEST, __FILE__, __LINE__))

#define LOG_DEBUG_SCOPED(scope) if(!SHOULD_LOG_DEBUG_SCOPED(scope)) ; else (::Ufora::Logging::Logger(LOG_LEVEL_DEBUG, __FILE__, __LINE__))
#define LOG_INFO_SCOPED(scope) if(!SHOULD_LOG_INFO_SCOPED(scope)) ; else ::Ufora::Logging::Logger(LOG_LEVEL_INFO, __FILE__, __LINE__)
#define LOG_WARN_SCOPED(scope) if(!SHOULD_LOG_WARN_SCOPED(scope)) ; else (::Ufora::Logging::Logger(LOG_LEVEL_WARN, __FILE__, __LINE__))
#define LOG_ERROR_SCOPED(scope) if(!SHOULD_LOG_ERROR_SCOPED(scope)) ; else (::Ufora::Logging::Logger(LOG_LEVEL_ERROR, __FILE__, __LINE__))
#define LOG_CRITICAL_SCOPED(scope) if(!SHOULD_LOG_CRITICAL_SCOPED(scope)) ; else (::Ufora::Logging::Logger(LOG_LEVEL_CRITICAL, __FILE__, __LINE__))
#define LOG_TEST_SCOPED(scope) if(!SHOULD_LOG_TEST_SCOPED(scope)) ; else (::Ufora::Logging::Logger(LOG_LEVEL_TEST, __FILE__, __LINE__))

#define LOGGER_DEBUG ::Ufora::Logging::Logger(LOG_LEVEL_DEBUG, __FILE__, __LINE__, SHOULD_LOG_DEBUG())
#define LOGGER_INFO ::Ufora::Logging::Logger(LOG_LEVEL_INFO, __FILE__, __LINE__, SHOULD_LOG_INFO())
#define LOGGER_WARN ::Ufora::Logging::Logger(LOG_LEVEL_WARN, __FILE__, __LINE__, SHOULD_LOG_WARN())
#define LOGGER_ERROR ::Ufora::Logging::Logger(LOG_LEVEL_ERROR, __FILE__, __LINE__, SHOULD_LOG_ERROR())
#define LOGGER_CRITICAL ::Ufora::Logging::Logger(LOG_LEVEL_CRITICAL, __FILE__, __LINE__, SHOULD_LOG_CRITICAL())
#define LOGGER_TEST ::Ufora::Logging::Logger(LOG_LEVEL_TEST, __FILE__, __LINE__, SHOULD_LOG_TEST())

#define LOGGER_DEBUG_SCOPED(scope) ::Ufora::Logging::Logger(LOG_LEVEL_DEBUG, __FILE__, __LINE__, SHOULD_LOG_DEBUG_SCOPED(scope))
#define LOGGER_INFO_SCOPED(scope) ::Ufora::Logging::Logger(LOG_LEVEL_INFO, __FILE__, __LINE__, SHOULD_LOG_INFO_SCOPED(scope))
#define LOGGER_WARN_SCOPED(scope) ::Ufora::Logging::Logger(LOG_LEVEL_WARN, __FILE__, __LINE__, SHOULD_LOG_WARN_SCOPED(scope))
#define LOGGER_ERROR_SCOPED(scope) ::Ufora::Logging::Logger(LOG_LEVEL_ERROR, __FILE__, __LINE__, SHOULD_LOG_ERROR_SCOPED(scope))
#define LOGGER_CRITICAL_SCOPED(scope) ::Ufora::Logging::Logger(LOG_LEVEL_CRITICAL, __FILE__, __LINE__, SHOULD_LOG_CRITICAL_SCOPED(scope))
#define LOGGER_TEST_SCOPED(scope) ::Ufora::Logging::Logger(LOG_LEVEL_TEST, __FILE__, __LINE__, SHOULD_LOG_TEST_SCOPED(scope))

#define LOGGER_DEBUG_T ::Ufora::Logging::Logger
#define LOGGER_INFO_T ::Ufora::Logging::Logger
#define LOGGER_WARN_T ::Ufora::Logging::Logger
#define LOGGER_ERROR_T ::Ufora::Logging::Logger
#define LOGGER_CRITICAL_T ::Ufora::Logging::Logger
#define LOGGER_TEST_T ::Ufora::Logging::Logger


namespace Ufora {

namespace Logging {

using LogWriter = std::function<void(LogLevel level, const char* filename, int lineNumber,
                                     const std::string& message)>;

void setLogLevel(LogLevel logLevel);

class Logger {
public:
    static void setLogWriter(LogWriter writer);

    static void logToStream(std::ostream& stream, LogLevel level, const char* filename, int lineNumber,
                            const std::string& message);

    Logger(LogLevel logLevel, const char * file, int line, bool shouldLog = true);

    Logger(const Logger& other);

    ~Logger();

    Logger& operator<<(const bool& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const int8_t& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const int16_t& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const int32_t& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const int64_t& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const uint8_t& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const uint16_t& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const uint32_t& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const uint64_t& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const double& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const float& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const std::string& in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<(const char* in)
        {
        mStringstream << in;
        return *this;
        }

    Logger& operator<<( std::ostream&(*streamer)(std::ostream& ) );

    Logger& operator<<( std::ios_base&(*streamer)(std::ios_base& ) );

    Logger& operator<<(const decltype(std::setw(0))& t)
        {
        mStringstream << t;
        return *this;
        }

    Logger& operator<<(const decltype(std::setprecision(0))& t)
        {
        mStringstream << t;
        return *this;
        }


    template<class T>
    Logger& operator<<(const T& t)
        {
        mStringstream << prettyPrintString(t);
        return *this;
        }


    static std::string logLevelToString(LogLevel level);

private:
    static LogWriter logWriter;

    const char* mFileName;

    int mLineNumber;

    LogLevel mLogLevel;

    std::ostringstream mStringstream;

    bool mShouldLog;
};

LogLevel** getScopedLoggingLevelHandle(const char* scope, const char* file);

void setScopedLoggingLevel(std::string scopeRegex, std::string fileRegex, LogLevel logLevel);

void resetScopedLoggingLevelToDefault(std::string scopeRegex, std::string fileRegex);

}

}

