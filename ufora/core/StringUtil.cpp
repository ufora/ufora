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
#include "StringUtil.hpp"
#include "Logging.hpp"
#include <boost/algorithm/string/replace.hpp>
#include <vector>

namespace Ufora {


std::string oneLineSanitization(const std::string& inText, uint32_t width)
	{
	std::string toUse = inText;
	if (toUse.size() > width)
		toUse.resize(width);

	if (inText.size() > width * 100)
		LOG_WARN << "Warning: oneLineSanitization chopping a string from "
			<< inText.size() << " to " << width;

	return substitute(substitute(toUse, "\n", " "), "\t", " ");
	}

std::string sanitizeFilename(const std::string& inFilename)
	{
	std::string tr = inFilename;

	for (long k = 0; k < tr.size();k++)
		if (!isalnum(tr[k])
				&& tr[k] != '.'
				&& tr[k] != '-'
				&& tr[k] != '<'
				&& tr[k] != '>'
				&& tr[k] != ':'
				)
			tr[k] = '_';

	return tr;
	}

std::string tabs(int32_t num)
	{
	std::string tr;
	while (num-- > 0)
		tr += "\t";
	return tr;
	}


std::string pad(const std::string& inText, long exactWidth, bool onRight, char sep)
	{
	if (onRight)
		{
		if (inText.size() < exactWidth)
			return std::string(exactWidth - inText.size(), sep) + inText;

		return inText.substr(inText.size() - exactWidth, exactWidth);
		}
	else
		{
		if (inText.size() < exactWidth)
			return inText + std::string(exactWidth - inText.size(), sep);

		return inText.substr(0, exactWidth);
		}
	}

std::string substitute(const std::string& inString,
						const std::string& search,
						const std::string& replace
						)
	{
	return boost::algorithm::replace_all_copy(inString, search, replace);
	}

std::string blockify(const std::string& inText)
	{
	return "    {\n    " + Ufora::substitute(inText, "\n", "\n    ") + "\n    }\n";
	}

std::string indent(const std::string& inText, int32_t times)
	{
	if (times <= 0)
		return inText;

	std::string indentation;
	indentation.resize(times*4, ' ');

	return indentation + Ufora::substitute(inText, "\n", "\n" + indentation);
	}

std::string indent(const std::string& inText,
				const std::string& withString,
				int32_t times
				)
	{
	if (times <= 0)
		return inText;

	if (times != 1)
		{
		std::string newWith;
		for (long k = 0; k < times;k++)
			newWith = newWith + withString;

		return indent(inText, newWith, 1);
		}
	else
		return withString + Ufora::substitute(inText, "\n", "\n" + withString);
	}

bool beginsWith(const std::string& toLookInside, const std::string& toFind)
	{
	if (toLookInside.size() < toFind.size())
		return false;

	return toLookInside.substr(0, toFind.size()) == toFind;
	}

bool endsWith(const std::string& toLookInside, const std::string& toFind)
	{
	if (toLookInside.size() < toFind.size())
		return false;

	return toLookInside.substr(toLookInside.size() - toFind.size()) == toFind;
	}

std::string makeColumns(long width, long cols, long minLength, std::string s)
	{
	//start by wrapping all the lines
	std::vector<std::string> lines;

	long last = 0;
	for (long k = 0; k <= s.size();k++)
		if (k == s.size() || s[k] == '\n')
			{
			std::string slice = s.substr(last, k - last);

			while (slice.size() > width)
				{
				lines.push_back(slice.substr(0,width));
				slice = slice.substr(width);
				}

			lines.push_back(slice);
			last = k + 1;
			}

	long colLength = std::max<long>(lines.size() / cols + 1, minLength);

	std::ostringstream str;

	for (long line = 0; line < colLength; line++)
		{
		for (long col = 0; col < cols; col++)
			if (line + col * colLength < lines.size())
				str << pad(lines[line + col * colLength], width) << "     ";
			else
				str << pad("", width) << "     ";

		str << "\n";
		}

	return str.str();
	}

}

