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
#include <new>

#include "AtomicOps.hpp"
#include "Logging.hpp"
#include "debug/StackTrace.hpp"
#include "lassert.hpp"

#include <gperftools/malloc_extension.h>
#include <gperftools/heap-profiler.h>

namespace Ufora {
namespace Memory {

size_t getMemoryStat(std::string inName)
	{
	size_t out = 0;

	if (MallocExtension::instance()->GetNumericProperty(inName.c_str(), &out));
		return out;

	return 0;
	}

void onAllocationFailed()
	{
	LOG_CRITICAL << "Out of memory. Aborting.";
	asm("int3");
	}

int setNewHandler()
	{
	std::set_new_handler(onAllocationFailed);
	return 0;
	}

int initNewHandler = setNewHandler();

void* bsa_malloc(size_t size)
	{
	void* tr = malloc(size);

	if (!tr)
		onAllocationFailed();
	
	return tr;
	}

void bsa_free(void* p)
	{
	free(p);
	}

void* bsa_realloc(void* ptr, size_t size)
	{
	void* tr = realloc(ptr, size);

	if (!tr)
		onAllocationFailed();

	return tr;
	}

size_t getTotalBytesAllocated(void)
	{
	return getMemoryStat("generic.current_allocated_bytes");
	}

size_t getTotalBytesRequestedFromOS(void)
	{
	return getMemoryStat("generic.heap_size");
	}

}
}

