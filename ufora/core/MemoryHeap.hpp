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

#include <boost/thread/shared_mutex.hpp>
#include <boost/tr1/functional.hpp>
#include <boost/unordered_map.hpp>
#include <cstdlib>
#include <vector>

#include "IntegerTypes.hpp"
#include "lassert.hpp"

/**
 * MemoryHeap represents a fake allocation heap to allow more granular control
 * over the memory layout within a process.  It allocates pages of memory from
 * the underlying system malloc, and then allows for malloc/free style
 * operations to manage memory within these pages.
 *
 * MemoryHeap *is not* thread safe.  Allocating and freeing memory within the
 * same MemoryHeap across threads is not supported.
 */
class MemoryHeap {
	typedef void* mspace;

	friend void* mmap_trampoline(size_t length);
	friend int munmap_trampoline(void* addr, size_t length);
	friend void* mremap_trampoline(void* addr, size_t oldLength, size_t newLength, int flags);

public:
	MemoryHeap(
		boost::function1<void*, size_t> inMMapFun,
		boost::function2<int, void*, size_t> inMUnmapFun,
		boost::function4<void*, void*, size_t, size_t, int> inMRemapFun
		);

	MemoryHeap(
		boost::function1<void*, size_t> inMMapFun,
		boost::function2<int, void*, size_t> inMUnmapFun,
		boost::function4<void*, void*, size_t, size_t, int> inMRemapFun,
		size_t pageSizeOverride
		);

	~MemoryHeap();

	// Memory allocation methods (not thread-safe)
	void*	malloc(size_t size);
	void free(void *ptr);
	void* realloc(void *ptr, size_t size);
	size_t msize(void *ptr);

	bool trim(size_t size);
	
	// Accounting methods (not thread-safe)
	size_t getBytesUsed() const;
	size_t getHeapSize() const;

	// Expensive debug functions
	void validate() const;

	//used only by free functions in the implementation
	void* mmap(size_t size);
    
    int munmap(void* addr, size_t size);

	void* mremap(void* addr, size_t oldSize, size_t newSize, int flags);

	size_t getLargeAllocSize() const;

	bool isLargeAlloc(void* addr) const;

	void detachLargeAlloc(void* addr);

private:
	void initialize();

	void mark_allocated(void* addr, size_t size, bool largeAlloc);
	int free_allocated();
	void mark_unallocated(void* addr, size_t size);


	struct alloc_info {
		const size_t size;
		const bool largeAlloc;

		alloc_info(const alloc_info &in) :
			size(in.size),
			largeAlloc(in.largeAlloc)
			{
			}

		alloc_info(size_t inSize, bool inLargeAlloc) :
			size(inSize),
			largeAlloc(inLargeAlloc)
			{
			lassert(inSize > 0);
			}
	};

	boost::unordered_map<void*, alloc_info> mPages;
	size_t mBytesUsed;
	size_t mHeapSize;

	mspace mMspace;

	boost::function1<void*, size_t> mMMapFun;
	boost::function2<int, void*, size_t> mMUnmapFun;
	boost::function4<void*, void*, size_t, size_t, int> mMRemapFun;

	size_t mPageSize;
	
public:
	static const size_t DEFAULT_PAGE_SIZE;
};

