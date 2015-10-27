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
#ifndef BSA_CORE_AtomicOps_hppml_
#define BSA_CORE_AtomicOps_hppml_


#include "Platform.hpp"

#include <stdint.h>

//include guard wrapper for atomic ops. should reimplement necessary functions on windows

#if defined(BSA_PLATFORM_LINUX) || defined(BSA_PLATFORM_APPLE)

	#if __x86_64__ || _WIN64
		
		typedef volatile int64_t AO_t;

	#else
		
		typedef volatile int32_t AO_t;

	#endif

	
	inline AO_t AO_fetch_and_add_full(AO_t* refcount, AO_t ct)
		{
		return __sync_fetch_and_add(refcount, ct);
		}
	
	inline AO_t AO_load(AO_t* value)
		{
		__sync_synchronize();
		return *value;
		}
	
	inline void AO_store(AO_t* value, AO_t toStore)
		{
		__sync_synchronize();
		*value = toStore;
		__sync_synchronize();
		}

	inline bool AO_compare_and_swap_full(AO_t* val, AO_t toCheckAgainst, AO_t toSwapInIfSuccessful)
		{
		return __sync_bool_compare_and_swap(val, toCheckAgainst, toSwapInIfSuccessful);
		}

	inline void fullMemoryBarrier()
		{
		__sync_synchronize();
		}

#else

	#if __x86_64__ || _WIN64
		
		typedef volatile uint64_t AO_t;

	#else
		
		typedef volatile __int32 AO_t;

	#endif


	AO_t AO_fetch_and_add_full(AO_t* refcount, AO_t ct);
	AO_t AO_load(AO_t* value);
	void AO_store(AO_t* value, AO_t toStore);
	bool AO_compare_and_swap_full(AO_t* val, AO_t toCheckAgainst, AO_t toSwapInIfSuccessful);

#endif






#endif

