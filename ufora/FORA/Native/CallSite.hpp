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
#ifndef INCL_CALL_SITE_HPP
#define INCL_CALL_SITE_HPP

#include <stdint.h>
#include <string>

#include "../../core/cppml/CPPMLPrettyPrinter.hppml"

//Uniquely identifies a specific call site in a certain function in native code.
class CallSite {
public:
	//The name of the function in which this call site resides.
	std::string callerName;
	
	//The numeric id of this call site for all generations of the calling
	//function. The actuall call operation in the NativeCFG is tagged with
	//this id.
	uint64_t siteId;
	
	//The name of the target function of this call site.
	std::string calleeName;
	
	CallSite();
	CallSite(const std::string& caller, uint64_t id, const std::string& callee);
};

//Indicates whether the given call sites are equal.
//Two call sites are said to be equal iff all of their
//fields are equal.
bool operator==(const CallSite& a, const CallSite& b);

//Indicates whether call site `a` is "less than" call site
//`b` under some unspecified partial order.
bool operator<(const CallSite& a, const CallSite& b);


template<>
class CPPMLPrettyPrint<CallSite> {
public:
	static void prettyPrint(CPPMLPrettyPrintStream& stream,
							const CallSite& cs) {
		stream << "CallSite(" << cs.callerName << ", " << cs.siteId << ")";
	}
};

#endif //INCL_CALL_SITE_HPP

