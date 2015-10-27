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
#ifndef INCLUDED_Exception_hpp
#define INCLUDED_Exception_hpp

#include <stdexcept>

#include "Platform.hpp"
#ifdef BSA_PLATFORM_APPLE
#include <string>
#endif

namespace Ufora {
	struct Exception : public std::logic_error {
		Exception(const std::string& msg) : std::logic_error(msg) {}
        Exception(const char * msg) : std::logic_error(msg) {}
	};

	struct PosixException : public Exception
		{
		PosixException(const std::string& msg, int errorCode) :
			Exception(msg + strerror(errorCode)) {}

		PosixException(const char* msg, int errorCode) :
			Exception(std::string(msg) + strerror(errorCode)) {}

		PosixException(int errorCode) : Exception(strerror(errorCode)) {}
		};

}

#endif

