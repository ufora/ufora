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
#include "CallSite.hpp"

using std::string;

CallSite::CallSite() : callerName(), siteId(), calleeName() { }

CallSite::CallSite(const string& caller, uint64_t id, const string& callee)
	: callerName(caller), siteId(id), calleeName(callee) { }

bool operator==(const CallSite& a, const CallSite& b) {
	return a.siteId == b.siteId &&
	       a.callerName == b.callerName &&
	       a.calleeName == b.calleeName;
}

bool operator<(const CallSite& a, const CallSite& b) {
	return
		a.siteId <  b.siteId || (
		a.siteId == b.siteId && (
			a.callerName <  b.callerName || (
			a.callerName == b.callerName &&
				a.calleeName < b.calleeName)));
}

