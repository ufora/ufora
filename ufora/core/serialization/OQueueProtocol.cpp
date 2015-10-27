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
#include "OQueueProtocol.hpp"


OQueueProtocol::OQueueProtocol(Queue<std::string>& inQueue) : 
	mQueue(inQueue),
	mPosition(0)
	{
	}

void OQueueProtocol::write(uword_t inByteCount, void *inData)
	{
	mQueue.write(std::string(static_cast<char*>(inData), inByteCount));
	mPosition += inByteCount;
	}

uword_t OQueueProtocol::position(void)
	{
	return mPosition;
	}


