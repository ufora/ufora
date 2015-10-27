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
#ifndef base_debug_StackTrace_H_
#define base_debug_StackTrace_H_

#include "../Platform.hpp"

#if BSA_PLATFORM_LINUX
#include <cxxabi.h>
#include <execinfo.h>
#endif


#include <vector>
#include <sstream>
#include <iostream>
#include <string>
#include <ctype.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <stdexcept>

namespace Ufora {
namespace debug {

class StackTrace {
private:
		StackTrace();
		StackTrace(const std::vector<void*> &inTrace);
		static bool isalpha(const std::string &inTrace);
public:
		StackTrace(const StackTrace& in);

		static std::string demangleStackSymbol(std::string s);
		static StackTrace	getTrace(int32_t inDepth = 40);
		static std::string	getStringTrace(int32_t inDepth = 40);
		std::string toString(void) const;
		static std::string	demangle(std::string s);

		static std::string	functionAddressToString(void* functionPtr);
private:
		std::vector<void*>			mTracePtrs;
		std::vector<std::string>	mDemangled;
}; //class StackTrace

} //namespace debug
} //namespace Ufora


void throwLogicErrorWithStacktrace(const std::string& inMessage = "");
std::logic_error standardLogicErrorWithStacktrace(const std::string& inMessage = "");

#endif

