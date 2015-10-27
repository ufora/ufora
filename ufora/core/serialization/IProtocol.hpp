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
#pragma once

#include "Common.hpp"

#include <stdexcept>

class IProtocol {
public:
	//request bytes from the stream. returns the number of bytes read. 
	//If inBlock is false, and no bytes are available, we return zero.
	//If inBlock is true, we return as many bytes as possible up to inByteCount.  If we return zero,
	//we have reached the end of the stream.
	//If the stream terminates unexpectedly, and we have unread bytes, we return those.
	//If the stream terminated unexpectedly and we have no unread bytes, we throw 
	//StreamTerminatedUnexpectedly
	virtual uword_t read(uword_t inByteCount, void *inData, bool inBlock) = 0;

	virtual uword_t position() = 0;
	
	class StreamTerminatedUnexpectedly : std::logic_error {
	public:
		StreamTerminatedUnexpectedly() : std::logic_error("Stream terminated unexpectedly")
			{
			}
	};
	
};


