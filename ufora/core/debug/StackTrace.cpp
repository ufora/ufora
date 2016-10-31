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
#include "StackTrace.hpp"
#include <stdexcept>
#include <string>
#include <sstream>
#include "../StringUtil.hpp"
#include <execinfo.h>

#include <cxxabi.h>

using namespace Ufora::debug;

StackTrace::StackTrace()
	{
	}

StackTrace::StackTrace(const std::vector<void*> &inTrace)
	{
	#if defined(__linux__) || defined(__APPLE__)

	mTracePtrs = inTrace;

	char** cs = backtrace_symbols(&inTrace[0], inTrace.size());

	mDemangled.clear();

	if (cs)
		{
		for (int32_t k = 0; k < mTracePtrs.size(); k++)
			mDemangled.push_back(demangleStackSymbol(cs[k]));

		free(cs);
		}
	#endif
	}

bool StackTrace::isalpha(const std::string &inTrace)
	{
	for (int32_t k = 0; k < inTrace.size(); k++)
		if (!isalnum(inTrace[k]) && inTrace[k] != '_')
			return false;
	return true;
	}

StackTrace::StackTrace(const StackTrace& in) :
		mTracePtrs(in.mTracePtrs),
		mDemangled(in.mDemangled)
	{
	}

std::string StackTrace::demangleStackSymbol(std::string s)
	{
	#if defined(__linux__) || defined(__APPLE__)
	if (s.find('(') != std::string::npos)
		{
		s = s.substr(s.find('(') + 1, s.find('+') - (s.find('(') + 1) );

		int32_t status;
		char* realname = 0;

		if (s.size() && isalpha(s))
			realname = abi::__cxa_demangle(s.c_str(), 0, 0, &status);

		if (realname)
			{
			s = std::string(realname);
			free(realname);
			}
			//else
			//s = "<ERR>";
		return s;
		}
		else
		return "<UNKNOWN>";
	#else
		return "StackTrace not implemented";
	#endif
	}

StackTrace	StackTrace::getTrace(int32_t inDepth)
	{
	#if defined(__linux__) || defined(__APPLE__)
		std::vector<void*>	trace;
		trace.resize(inDepth);
		trace.resize(backtrace(&trace[0], trace.size()));
		return StackTrace(trace);
	#else
		return StackTrace();
	#endif
	}

std::string	StackTrace::getStringTrace(int32_t inDepth)
	{
	#if defined(__linux__) || defined(__APPLE__)
		return getTrace().toString();
	#else
		return std::string("StackTrace not implemented\n");
	#endif
	}

std::string StackTrace::toString(void) const
	{
	#if defined(__linux__) || defined(__APPLE__)
		std::ostringstream s;
		for (int32_t k = 0; k < mDemangled.size(); k++)
			s << mDemangled[k] << "\n";
		return s.str();
	#else
		return std::string("StackTrace not implemented\n");
	#endif
	}

std::string	StackTrace::demangle(std::string s)
	{
	#if defined(__linux__) || defined(__APPLE__)
		int32_t status;
		char* realname = abi::__cxa_demangle(s.c_str(), 0, 0, &status);
		if (realname)
			{
			s = std::string(realname);
			free(realname);
			return s;
			}
		return "<ERR>";
	#else
		return Ufora::substitute(s, "class ","");
	#endif
	}

std::string	StackTrace::functionAddressToString(void* functionPtr)
	{
	#if defined(__linux__) || defined(__APPLE__)

	char** cs = backtrace_symbols(&functionPtr, 1);

	if (cs)
		{
		std::string result = demangleStackSymbol(cs[0]);

		free(cs);

		return result;
		}
	#endif

	//default case
	std::ostringstream s;
	s << functionPtr;
	return s.str();
	}

void throwLogicErrorWithStacktrace(const std::string& inMessage)
	{
	throw std::logic_error(inMessage + "\n\nStack Trace = \n"
				+ Ufora::debug::StackTrace::getStringTrace());
	}

std::logic_error standardLogicErrorWithStacktrace(const std::string& inMessage)
	{
	return std::logic_error(
		inMessage + "\n\nStack Trace = \n"
			+ Ufora::debug::StackTrace::getStringTrace()
		);
	}


