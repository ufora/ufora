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
#include <string>

#include "time.h"
#include "Platform.hpp"

#ifdef BSA_PLATFORM_LINUX
#include <unistd.h>
#endif // BSA_PLATFORM_LINUX

#ifdef BSA_PLATFORM_APPLE
typedef enum {
	CLOCK_REALTIME,
	CLOCK_MONOTONIC,
	CLOCK_PROCESS_CPUTIME_ID,
	CLOCK_THREAD_CPUTIME_ID
} clockid_t;

int32_t clock_gettime(clockid_t clk_id, struct timespec *tp);
#endif // BSA_PLATFORM_APPLE

void sleepSeconds(double inTime);

double curClock(void);

//number of seconds of processor time used by this thread
double curThreadClock(void);

std::string currentTimeAsString();

