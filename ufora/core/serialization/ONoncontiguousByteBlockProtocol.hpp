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
#include <deque>
#include "Common.hpp"
#include "OProtocol.hpp"
#include "NoncontiguousByteBlock.hpp"

//protocol that holds data in chunks of memory, and can push them into a string. avoids big reallocs
class ONoncontiguousByteBlockProtocol : public OProtocol {
public:
	ONoncontiguousByteBlockProtocol();
	ONoncontiguousByteBlockProtocol(ONoncontiguousByteBlockProtocol& in) = delete;
	ONoncontiguousByteBlockProtocol& operator=(const ONoncontiguousByteBlockProtocol& in) = delete;

	~ONoncontiguousByteBlockProtocol();

	void write(uword_t inByteCount, void *inData);

	uword_t position(void);

	/// \brief Return the current Protocol's and clear it.
	PolymorphicSharedPtr<NoncontiguousByteBlock> getData(void);

private:
	PolymorphicSharedPtr<NoncontiguousByteBlock> mData;

	uword_t mPosition;
};

