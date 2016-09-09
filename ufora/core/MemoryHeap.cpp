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
#include "MemoryUtil.hpp"
#include "MemoryHeap.hpp"

#include <sys/mman.h>

#include "lassert.hpp"
#include "Logging.hpp"


#define ONLY_MSPACES 1 // We only need the 'mspaces' variants of the malloc functions
#define HAVE_MORECORE 0
#define HAVE_MREMAP 1

#define mmap_trampoline(length) (curMemoryHeap->mmap(length))

#define munmap_trampoline(addr, length) (curMemoryHeap->munmap(addr, length))

#define mremap_trampoline(addr, oldLength, newLength, flags) (curMemoryHeap->mremap(addr, oldLength, newLength, flags))

//these modify the behavior of 'dlmalloc/malloc.c' included below.

#define DIRECT_MMAP mmap_trampoline
#define MMAP mmap_trampoline
#define MUNMAP munmap_trampoline
#define MREMAP mremap_trampoline

#include <dlmalloc/malloc.inc>

const size_t MemoryHeap::DEFAULT_PAGE_SIZE = 256 * 1024;

MemoryHeap::MemoryHeap(
				boost::function1<void*, size_t> inMMapFun,
				boost::function2<int, void*, size_t> inMUnmapFun,
				boost::function4<void*, void*, size_t, size_t, int> inMRemapFun
				) :
		mMMapFun(inMMapFun),
		mMUnmapFun(inMUnmapFun),
		mMRemapFun(inMRemapFun),
		mBytesUsed(0),
		mHeapSize(0),
		mMspace(NULL),
		mPageSize(DEFAULT_PAGE_SIZE)
	{
	}

MemoryHeap::MemoryHeap(
				boost::function1<void*, size_t> inMMapFun,
				boost::function2<int, void*, size_t> inMUnmapFun,
				boost::function4<void*, void*, size_t, size_t, int> inMRemapFun,
				size_t pageSizeOverride
				) :
		mMMapFun(inMMapFun),
		mMUnmapFun(inMUnmapFun),
		mMRemapFun(inMRemapFun),
		mBytesUsed(0),
		mHeapSize(0),
		mMspace(NULL),
		mPageSize(pageSizeOverride)
	{
	}

MemoryHeap::~MemoryHeap()
	{
	if (mMspace == NULL)
		return;

	size_t used = getHeapSize();
	size_t freed = destroy_mspace(mMspace);
	freed += free_allocated();

	lassert(used == freed);
	lassert(mPages.size() == 0);
	}

void MemoryHeap::initialize()
	{
	mMspace = create_mspace_with_granularity(mPageSize, 0, this);

	mspace_track_large_chunks(mMspace, 1);

	lassert(mPageSize == mspace_footprint(mMspace));
	}

int MemoryHeap::free_allocated()
	{
	size_t freed = 0;

	auto itr=mPages.begin();
	while (itr != mPages.end())
		{
		std::pair<void*, alloc_info> ptr = *itr;
		lassert(ptr.second.size > 0);
		mMUnmapFun(ptr.first, ptr.second.size);
		freed += ptr.second.size;
		itr++;
		}

	mPages.clear();
	return freed;
	}

void MemoryHeap::mark_allocated(void* addr, size_t size, bool largeAlloc)
	{
	lassert(size > 0);
	mPages.insert(std::make_pair(addr, alloc_info(size, largeAlloc)));
	mHeapSize += size;
	}

void MemoryHeap::mark_unallocated(void* addr, size_t size)
	{
	while (size > 0)
		{
		auto itr = mPages.find(addr);
		std::pair<void*, alloc_info> info = *itr;
		lassert_dump(itr != mPages.end(), "could not find page in memory");

		lassert(info.second.size <= size);
		mPages.erase(itr);

		mHeapSize -= info.second.size;
		size -= info.second.size;
		addr = (void*)((uint64_t)addr + info.second.size);
		}
	}

void* MemoryHeap::mmap(size_t size)
	{
	void* newAddr = mMMapFun(size);

	if (newAddr != MAP_FAILED)
		mark_allocated(newAddr, size, false);

	return newAddr;
	}

int MemoryHeap::munmap(void* addr, size_t size)
	{
	int result = mMUnmapFun(addr, size);

	if (result != -1)
		mark_unallocated(addr, size);

	return result;
	}

void* MemoryHeap::mremap(void* addr, size_t oldSize, size_t newSize, int flags)
	{
	if (oldSize == newSize)
		return addr;

	void* newAddr = mMRemapFun(addr, oldSize, newSize, flags);

	if (newAddr != MAP_FAILED)
		{
		mark_unallocated(addr, oldSize);
		mark_allocated(newAddr, newSize, false);
		}

	return newAddr;
	}

void*	MemoryHeap::malloc(size_t size)
	{
	if (mMspace == NULL)
		initialize();

	if (size >= mPageSize)
		{
		void* newAddr = mMMapFun(size);

		if (newAddr != MAP_FAILED)
			{
			mBytesUsed += size;
			mark_allocated(newAddr, size, true);
			return newAddr;
			}

		return 0;
		}

	void* newAddr = mspace_malloc(mMspace, size);
	if (newAddr != NULL)
		mBytesUsed += mspace_usable_size(newAddr);
	return newAddr;
	}

void MemoryHeap::free(void *ptr)
	{
	if (mMspace == NULL) return;

	auto itr = mPages.find(ptr);

	if (itr != mPages.end())
		{
		alloc_info info = (*itr).second;
		if (info.largeAlloc)
			{
			mMUnmapFun(ptr, info.size);

			mark_unallocated(ptr, info.size);
			mBytesUsed -= info.size;
			return;
			}
		}

	mBytesUsed -= mspace_usable_size(ptr);
	lassert(mspace_usable_size(ptr));
	mspace_free(mMspace, ptr);
	}

void* MemoryHeap::realloc(void *ptr, size_t size)
	{
	if (mMspace == NULL)
		return 0;

	auto itr = mPages.find(ptr);

	if (itr != mPages.end())
		{
		alloc_info info = (*itr).second;

		if (info.largeAlloc)
			{
			if (size < mPageSize / 2)
				{
				lassert(size < info.size);

				//the new array is no longer a 'large alloc' and should be placed back in the main
				//pool
				void* newPtr = malloc(size);
				lassert(newPtr);
				memcpy(newPtr, ptr, size);
				free(ptr);
				return newPtr;
				}
			else
				{
				void* newPtr = mMRemapFun(ptr, info.size, size, MREMAP_MAYMOVE);

				if (newPtr == MAP_FAILED)
					return 0;

				mark_unallocated(ptr, info.size);
				mark_allocated(newPtr, size, info.largeAlloc);
				mBytesUsed += (size - info.size);
				return newPtr;
				}
			}
		}

	size_t oldSize = mspace_usable_size(ptr);

	//the new array will be large enough that we should mmap it.
	if (size >= mPageSize)
		{
		void* newPtr = malloc(size);
		lassert(newPtr);
		memcpy(newPtr, ptr, std::min<size_t>(oldSize, size));
		free(ptr);
		return newPtr;
		}

	void* newPtr = mspace_realloc(mMspace, ptr, size);
	if (newPtr != NULL)
		mBytesUsed += mspace_usable_size(newPtr) - oldSize;
	return newPtr;
	}

size_t MemoryHeap::msize(void* ptr)
	{
	if (mMspace == NULL) return 0;

	auto itr = mPages.find(ptr);

	if (itr != mPages.end())
		{
		alloc_info info = (*itr).second;
		if (info.largeAlloc) { return info.size; }
		}

	return mspace_usable_size(ptr);
	}

bool MemoryHeap::trim(size_t pad)
	{
	size_t released = release_unused_segments((mstate)mMspace);
	int trimmed = mspace_trim(mMspace, pad);
	return released > 0 || trimmed > 0;
	}

void MemoryHeap::validate() const
	{
	if (mMspace == NULL) return;
	lassert(mBytesUsed < mHeapSize);

	for (auto itr=mPages.begin(); itr!=mPages.end(); ++itr)
		{
		std::pair<void*, alloc_info> info = *itr;

		lassert(info.second.size > 0);
		}
	}

size_t MemoryHeap::getBytesUsed() const
	{
	return mBytesUsed;
	}

size_t MemoryHeap::getHeapSize() const
	{
	return mHeapSize;
	}

bool MemoryHeap::isLargeAlloc(void* ptr) const
	{
	auto itr = mPages.find(ptr);

	if (itr != mPages.end())
		{
		alloc_info info = (*itr).second;
		if (info.largeAlloc)
			return true;
		}

	return false;
	}

void MemoryHeap::detachLargeAlloc(void* ptr)
	{
	auto itr = mPages.find(ptr);

	if (itr != mPages.end())
		{
		alloc_info info = (*itr).second;
		if (info.largeAlloc)
			{
			mark_unallocated(ptr, info.size);
			mBytesUsed -= info.size;
			return;
			}
		}

	lassert(false);
	}

size_t MemoryHeap::getLargeAllocSize() const
	{
	return mPageSize;
	}
