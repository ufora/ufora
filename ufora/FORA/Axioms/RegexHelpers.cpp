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
#include "RegexHelpers.hpp"

#include "../../core/threading/ThreadSafeMap.hpp"

boost::regex getRegexFromCache(const String& inString)
	{
	//TODO BUG anybody: ensure that we don't get too many regexes and run out of RAM
	static ThreadSafeMap<hash_type, boost::regex> parsedRegexes;

	static ThreadSafeMap<hash_type, std::string> badRegexes;

	Nullable<boost::regex> nRegex = parsedRegexes.get(inString.hash());
	if (nRegex)
		return *nRegex;

	Nullable<std::string> nError = badRegexes.get(inString.hash());

	if (nError)
		throw std::logic_error(*nError);

	try {
		boost::regex regex(inString.c_str());

		parsedRegexes.set(
			inString.hash(), 
			regex
			);

		return regex;
		}
	catch(boost::regex_error& err)
		{
		badRegexes.set(inString.hash(), err.what());
		throw std::logic_error(err.what());
		}
	}
		

