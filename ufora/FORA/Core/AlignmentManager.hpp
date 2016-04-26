/***************************************************************************
    Copyright 2015,2016 Ufora Inc.

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

#include "../../core/containers/ImmutableTreeSet.hppml"
#include "../../core/IntegerTypes.hpp"

class ImplValContainer;
class MemoryPool;


class AlignmentManager {
public:
	AlignmentManager(bool freeAllocatedMemoryOnDestroy=true);
	AlignmentManager(MemoryPool* pool, bool freeAllocatedMemoryOnDestroy=true);
	~AlignmentManager();

	uint8_t* getHandleToAlignedData(const ImplValContainer& value);
	uint8_t* allocateAlignedData(const Type& type, uword_t count);

private:
	ImmutableTreeSet<uint8_t*> mManagedMemory;
	MemoryPool *mPool;
	bool mFreeOnDestroy;
};
