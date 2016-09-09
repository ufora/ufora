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
#include <cstdlib>

namespace Ufora {
namespace Memory {

// our own memory allocator
void* bsa_malloc(size_t size);
void* bsa_realloc(void* p, size_t size);
void bsa_free(void* p);

size_t getTotalBytesAllocated(void);
size_t getTotalBytesRequestedFromOS(void);

}
}

