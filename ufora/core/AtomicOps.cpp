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
#include "AtomicOps.hpp"

#if BSA_PLATFORM_LINUX

#endif

#if BSA_PLATFORM_WINDOWS

#include <Windows.h>

//nonatomic implementation that should work single-threaded
AO_t AO_fetch_and_add_full(AO_t* refcount, AO_t ct)
	{
	return InterlockedAdd64(refcount, ct) - ct;
	}
AO_t AO_load(AO_t* value)
	{
	return *value;
	}

void AO_store(AO_t* value, AO_t toStore)
	{
	value[0] = toStore;
	}
bool AO_compare_and_swap_full(AO_t* val, AO_t toCheckAgainst, AO_t toSwapInIfSuccessful)
	{
	return InterlockedCompareExchange64(val, toSwapInIfSuccessful, toCheckAgainst) == toCheckAgainst;
	}

#endif

