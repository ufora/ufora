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

#include <vector>
#include <string>
#include "../lassert.hpp"
#include "IProtocol.hpp"
#include "../Common.hppml"

class IMemProtocol : public IProtocol {
public:
	IMemProtocol(const IMemProtocol& in) = delete;
	IMemProtocol& operator=(const IMemProtocol& in) = delete;
	//note that 'inData' must remain alive for the duration of the operation. we don't copy it.
	IMemProtocol(const char* inData, uword_t inSize, uword_t inPosition = 0);

	//note that 'inData' must remain alive for the duration of the operation. we don't copy it.
	IMemProtocol(const std::string& inData, uword_t inPosition = 0);

	//note that 'inData' must remain alive for the duration of the operation. we don't copy it.
	IMemProtocol(const std::vector<char>& inData, uword_t inPosition = 0);

	uword_t read(uword_t inByteCount, void *inData, bool inBlock);

	void reset(const char* inData, uword_t inSize, uword_t inPosition = 0);

	void reset(const std::string& inData, uword_t inPosition = 0);

	void reset(const std::vector<char>& inData, uword_t inPosition = 0);

	uword_t position(void);

private:
	const char* mData;

	uword_t	mDataSize;

	uword_t mPosition;
};

