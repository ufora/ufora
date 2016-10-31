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
#ifndef INCL_CALL_SITE_COUNTER_HPP
#define INCL_CALL_SITE_COUNTER_HPP

#include <boost/shared_ptr.hpp>
#include "../../core/cppml/CPPMLPrettyPrinter.hppml"
#include "../../core/Common.hppml" //for uword_t, uint64_t, etc.

class CallSiteCounter {
private:
	//Right now, the referenced memory is never deallocated.
	uint64_t* const mPtr;

public:
	CallSiteCounter();
	//Use the default destructor.
	//Use the default copy constructor and operator=.
	uint64_t get() const;
	void reset();
	uint64_t* getAddr();
};

template<>
class CPPMLPrettyPrint<CallSiteCounter> {
public:
	static void prettyPrint(CPPMLPrettyPrintStream& s,
							CallSiteCounter t)
		{
		s << "CallSiteCounter(ptr = " << (void*)t.getAddr()
		  << ", count = " << t.get() << ")";
		}
};

#endif //INCL_CALL_SITE_COUNTER_HPP

