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
#include <stdint.h>

//typedef signed and unsigned word types for the current machine
#if __x86_64__ || defined(_WIN64)
	typedef uint64_t	uword_t;
	typedef int64_t		sword_t;

	static_assert(sizeof(uint64_t) == 8, "uint64_t is not 8 bytes long.");
	static_assert(sizeof(int64_t) == 8, "int64_t is not 8 bytes long.");
#else
typedef uint32_t	uword_t;
typedef int32_t		sword_t;
#endif

static_assert(sizeof(uint32_t) == 4, "uint32_t is not 4 bytes long.");
static_assert(sizeof(int32_t) == 4, "int32_t is not 4 bytes long.");
static_assert(sizeof(uint16_t) == 2, "int16_t is not 2 bytes long.");
static_assert(sizeof(int16_t) == 2, "int16_t is not 2 bytes long.");
static_assert(sizeof(uint8_t) == 1, "int8_t is not 1 byte long.");
static_assert(sizeof(int8_t) == 1, "int8_t is not 1 byte long.");

