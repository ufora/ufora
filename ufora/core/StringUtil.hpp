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
#ifndef core_StringUtil_hpp_
#define core_StringUtil_hpp_

#include <string>
#include <stdint.h>

namespace Ufora {

std::string tabs(int32_t num);

std::string substitute(	const std::string& inString,
						const std::string& search,
						const std::string& replace);

std::string blockify(const std::string& inText);

std::string pad(const std::string& inText, long exactWidth, bool onRight = false, char sep = ' ');

std::string indent(const std::string& inText, int32_t times = 1);

std::string indent(	const std::string& inText,
					const std::string& withString,
					int32_t times = 1);

std::string oneLineSanitization(const std::string& inText, uint32_t width = 80);

std::string sanitizeFilename(const std::string& inFilename);

bool beginsWith(const std::string& toLookInside, const std::string& toFind);

bool endsWith(const std::string& toLookInside, const std::string& toFind);

std::string makeColumns(long width, long cols, long minLength, std::string s);

}
#endif

