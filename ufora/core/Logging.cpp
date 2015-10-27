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

#include "Logging.hpp"
#include "ScopedLoggingHandles.hppml"

#include <sstream>
#include <iostream> // for std::cerr
#include <algorithm>
#include <vector>
#include <stdio.h>
#include <string>
#include <sstream>
//#include <regex>

#include "Clock.hpp"
#include <boost/thread.hpp>
#include <boost/regex.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/lambda/construct.hpp>

namespace {
    const char* filenameFromPath(const char* path)
        {
        size_t len = strlen(path);
        for (const char* p = path + len; p > path; --p)
            if (*p == '/' or *p == '\\')
                return p + 1;
        return path;
        }

    std::string getMessagePrefix(
            const std::string& logLevelLabel, 
            const char* inSourceFile,
            int inLineNumber)
        {
        char lineNoStr[10]; 
        snprintf(lineNoStr, sizeof(lineNoStr), ":%-6d: ", inLineNumber);

        std::stringstream s;
        s << currentTimeAsString() << " "
          << logLevelLabel << " "
          << filenameFromPath(inSourceFile)
          << lineNoStr;
        return s.str();
        }

    void indentLogOstream(const std::string& message, const std::string& indent, std::ostream& out)
        {
        using namespace std;
        std::string indentPrefix = std::string(indent.size() - 2, ' ') + ": ";

        bool firstLine = true;
        std::size_t lastPos = 0;
        std::size_t pos = message.find('\n');

        while(lastPos != std::string::npos)
            {
            std::size_t numCharsToWrite = message.size() - lastPos;
            if (pos != std::string::npos)
                {
                pos++;
                numCharsToWrite = pos - lastPos;
                }

            if (firstLine)
                {
                out << indent;
                firstLine = false;
                }
            else
                out << indentPrefix;

            int bytesToWrite = pos - lastPos;
            if (pos == string::npos)
                bytesToWrite = message.size() - lastPos;

            out.write(message.c_str() + lastPos, bytesToWrite);
            lastPos = pos;
            pos = message.find('\n', pos);
            }
        }
}

namespace Ufora {
namespace Logging {

void writeLog(
        LogLevel level, 
        const char*  filename, 
        int lineNumber, 
        const std::string& message)
    {
    std::string logLevelLabel(Ufora::Logging::Logger::logLevelToString(level));
    std::string firstLinePrefix(getMessagePrefix(logLevelLabel, filename, lineNumber));

    static boost::mutex m;
    boost::lock_guard<boost::mutex> g(m);
    std::ostringstream stream;

    indentLogOstream(message, firstLinePrefix, stream);

    std::cerr << stream.str() << std::endl;
    }

LogLevel& getLogLevel(void)
    {
    static LogLevel logLevel = LOG_LEVEL_INFO;
    return logLevel;
    }

void setLogLevel(LogLevel logLevel)
    {
    getLogLevel() = logLevel;
    }

Logger::Logger(LogLevel logLevel, const char * file, int line, bool shouldLog) : 
        mFileName(file),
        mLineNumber(line),
        mLogLevel(logLevel),
        mShouldLog(shouldLog)

    {
    }

Logger::Logger(const Logger& other)
    : mStringstream(other.mStringstream.str())
    {}



void Logger::logToStream(std::ostream& stream, LogLevel level, const char* filename, 
        int lineNumber, const std::string& message)
    {
    indentLogOstream(
        message,
        getMessagePrefix(logLevelToString(level), filename, lineNumber), 
        stream
        );
    }

void Logger::logToStderr(LogLevel level, const char* filename, 
        int lineNumber, const std::string& message)
    {
    logToStream(std::cerr, level, filename, lineNumber, message);
    }

Logger::~Logger()
    {
    if (mShouldLog)
        writeLog(mLogLevel, mFileName, mLineNumber, mStringstream.str());
    }

Logger& Logger::operator<<( std::ostream&(*streamer)(std::ostream& ) )
    {
    mStringstream << streamer;
    return *this;
    }

Logger& Logger::operator<<( std::ios_base&(*streamer)(std::ios_base& ) )
    {
    mStringstream << streamer;
    return *this;
    }

std::string Logger::logLevelToString(LogLevel level)
    {
    switch (level)
        {
        case LOG_LEVEL_DEBUG:
            return "DEBUG";
        case LOG_LEVEL_INFO:
            return "INFO";
        case LOG_LEVEL_WARN:
            return "WARN";
        case LOG_LEVEL_ERROR:
            return "ERROR";
        case LOG_LEVEL_CRITICAL:
            return "CRITICAL";
        case LOG_LEVEL_TEST:
            return "TEST";
        default:
            assert(false);
            return "UNEXPECTED";
        }
    }


Ufora::ScopedLoggingHandles& scopedLoggingHandlesSingleton()
    {
    static Ufora::ScopedLoggingHandles result(&getLogLevel());

    return result;
    }

LogLevel** getScopedLoggingLevelHandle(const char* scope, const char* file)
    {
    return scopedLoggingHandlesSingleton().getHandle(
        Ufora::ScopedLoggingEntry(scope, file)
        );
    }

void setScopedLoggingLevel(std::string scopeRegex, std::string fileRegex, LogLevel level)
    {
    scopedLoggingHandlesSingleton().addPattern(
        Ufora::ScopedLoggingEntry(scopeRegex, fileRegex),
        null() << level
        );
    }

void resetScopedLoggingLevelToDefault(std::string scopeRegex, std::string fileRegex)
    {
    scopedLoggingHandlesSingleton().addPattern(
        Ufora::ScopedLoggingEntry(scopeRegex, fileRegex),
        null()
        );
    }

}
}

