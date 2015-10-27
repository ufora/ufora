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
#include "../Common.hppml"
#include "OProtocol.hpp"
#include <stdio.h>

class OFileProtocol : public OProtocol {
	OFileProtocol(const OFileProtocol& in);
	OFileProtocol& operator=(const OFileProtocol& in);
public:
	enum class CloseOnDestroy { True, False };

	OFileProtocol(FILE* inFile, CloseOnDestroy closeOnDestroy = CloseOnDestroy::False) :
			mFile(inFile),
			mPosition(0),
			mCloseOnDestroy(closeOnDestroy)
		{
		}

	~OFileProtocol()
		{
		if (mCloseOnDestroy == CloseOnDestroy::True && mFile)
			fclose(mFile);
		}
		
	void write(uword_t inByteCount, void *inData)
		{
		mPosition += inByteCount;
		::fwrite(inData, 1, inByteCount, mFile);
		}

	uword_t position(void)
		{
		return mPosition;
		}

private:
	uword_t mPosition;

	FILE* mFile;

	CloseOnDestroy mCloseOnDestroy;
};


