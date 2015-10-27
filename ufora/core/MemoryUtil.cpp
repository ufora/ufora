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
#include <sys/mman.h>
#include <string.h>
#include "lassert.hpp"
#include "Logging.hpp"

#ifdef BSA_PLATFORM_APPLE

// A replacement for the missing mremap() function on Darwin.
void* mremap(void* old_address, size_t old_size, size_t new_size, int flags)
	{
	// TODO: We may need to assert that old_size and new_size align to page boundaries

	if (new_size < old_size)
		{
		int result = munmap((void*) ((unsigned long)old_address + new_size), old_size - new_size);
		if (result == 0)
			return old_address;
		else
			return (void*)result;
		}
	else if (new_size > old_size)
		{
        // XXX This is not efficient, but it works for now. william 2013-07-07

        void* result = mmap(0, new_size, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);

        if (result == (void*)-1)
            return result;

        memcpy(result, old_address, old_size);
        munmap(old_address, old_size);

        return result;
		}
    else
        {
        return old_address;
        }
	}

#endif


