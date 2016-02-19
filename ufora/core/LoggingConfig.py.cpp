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
#include "../native/module.hpp"
#include "Platform.hpp"
#include "Logging.hpp"

#include <stdint.h>
#include <boost/python.hpp>
#include "../native/Registrar.hpp"
#include "python/CPPMLWrapper.hpp"

class LoggingConfigWrapper :
	public native::module::Exporter<LoggingConfigWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "Logging";
		}

	static LogLevel convertLevelFromPy(int logLevel)
		{
		return static_cast<LogLevel>((logLevel / 10) - 1);
		}

	static bool shouldLog(int logLevel)
		{
		LogLevel level = convertLevelFromPy(logLevel);
		switch (level)
			{
			case LOG_LEVEL_DEBUG:
				return SHOULD_LOG_DEBUG();
			case LOG_LEVEL_INFO:
				return SHOULD_LOG_INFO();
			case LOG_LEVEL_WARN:
				return SHOULD_LOG_WARN();
			case LOG_LEVEL_ERROR:
				return SHOULD_LOG_ERROR();
			case LOG_LEVEL_CRITICAL:
				return SHOULD_LOG_CRITICAL();
			default:
				lassert_dump(false, "Invalid log level:" << logLevel);
			}
		}
	static void logPy(int logLevel, std::string message)
		{
		// convert from python log levels
		int level = convertLevelFromPy(logLevel);
		switch (level)
			{
			case LOG_LEVEL_DEBUG:
				LOG_DEBUG << message;
				return;
			case LOG_LEVEL_INFO:
				LOG_INFO << message;
				return;
			case LOG_LEVEL_WARN:
				LOG_WARN << message;
				return;
			case LOG_LEVEL_ERROR:
				LOG_ERROR << message;
				return;
			case LOG_LEVEL_CRITICAL:
				LOG_CRITICAL << message;
				return;
			default:
				assert(false);
			}
		}

	static void logInfo(std::string i)
		{
		LOG_INFO << i;
		}

	static void logDebug(std::string i)
		{
		LOG_DEBUG << i;
		}

	static void setLogLevelPy(int logLevel)
		{
		Ufora::Logging::setLogLevel(convertLevelFromPy(logLevel));
		}

	static void setScopedLoggingLevel(std::string scopeRegex, std::string fileRegex, int logLevel)
		{
		Ufora::Logging::setScopedLoggingLevel(scopeRegex, fileRegex, convertLevelFromPy(logLevel));
		}

	static void resetScopedLoggingLevelToDefault(std::string scopeRegex, std::string fileRegex)
		{
		Ufora::Logging::resetScopedLoggingLevelToDefault(scopeRegex, fileRegex);
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;
		def("setLogLevel", setLogLevelPy);
		def("shouldLog", shouldLog);
		def("log", logPy);
		def("logInfo", logInfo);
		def("logDebug", logDebug);
		def("setScopedLoggingLevel", setScopedLoggingLevel);
		def("resetScopedLoggingLevelToDefault", resetScopedLoggingLevelToDefault);
		}
};


//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<LoggingConfigWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<LoggingConfigWrapper>::registerWrapper();

