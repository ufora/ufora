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

class ImplValContainer;
class MemoryPool;
class NativeType;
class Type;

namespace TypedFora {
namespace Abi {

class VectorRecord;

}
}


class CudaVectorRecordStorage {
public:
	uint8_t*		mDataPtr;
	uint64_t		mSize;
	uint64_t		mOffset;
	int64_t			mStride;

};

class AlignmentManager {
public:
	AlignmentManager(bool freeAllocatedMemoryOnDestroy=true);
	
	AlignmentManager(MemoryPool* pool, bool freeAllocatedMemoryOnDestroy=true);
	
	~AlignmentManager();

	uint8_t* getHandleToCudaAlignedData(const ImplValContainer& value);
	
	uint8_t* allocateCudaMemory(uword_t bytecount);

private:
	std::set<uint8_t*> mManagedMemory;

	std::set<uint8_t*> mCudaManagedMemory;

	MemoryPool *mPool;

	bool mFreeOnDestroy;
	
	static void copyVectorToAlignedMemory(
			CudaVectorRecordStorage& target,
			TypedFora::Abi::VectorRecord& source,
			boost::function<uint8_t* (uword_t bytecount)> allocator
			);

	static void copyObjectsToAlignedMemory(
			uint8_t* targetMemory,
			uint8_t* sourceMemory,
			::Type objectType,
			uint64_t objectCount,
			uint64_t destStride,
			uint64_t sourceStride,
			boost::function<uint8_t* (uword_t bytecount)> allocator
			);
};
