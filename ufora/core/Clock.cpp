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
#include "Clock.hpp"
#include "Windows.hpp"
#include <stdint.h>
#include <stdio.h>
#include <ctime>

#ifdef BSA_PLATFORM_APPLE

#endif // BSA_PLATFORM_APPLE

#ifdef BSA_PLATFORM_WINDOWS

void sleepSeconds(double inTime)
	{
	//call the win32 Sleep function, which takes milliseconds
	Sleep(inTime * 1000);
	}

double curClock(void)
	{
	FILETIME lpSystemTimeAsFileTime;
	GetSystemTimeAsFileTime(&lpSystemTimeAsFileTime);
	
	//unpack to a double.
	//this technique comes from
	//http://msdn.microsoft.com/en-us/library/windows/desktop/ms724284%28v=vs.85%29.aspx
	
	ULARGE_INTEGER largeInt;
	largeInt.LowPart = lpSystemTimeAsFileTime.dwLowDateTime;
	largeInt.HighPart = lpSystemTimeAsFileTime.dwHighDateTime;
	
	//precision is 100 nanoseconds
	return (double)largeInt.QuadPart / (double)10000000;
	}

double curThreadClock(void)
	{
	lassert_dump(false, "not implemented");
	}

#elif defined(BSA_PLATFORM_LINUX) || defined(BSA_PLATFORM_APPLE)

#include <sys/time.h>

#ifdef BSA_PLATFORM_APPLE
#include "OSXClock.hpp"
#endif

void sleepSeconds(double inTime)
	{
	int64_t usec = inTime * 1000000;

	int32_t secs = usec / 1000000;
	usec = usec % 1000000;
	if (secs)
		sleep(secs);
	usleep( usec );
	}

double curClock(void)
	{
	timespec ts;

	clock_gettime(CLOCK_REALTIME, &ts); // Works on Linux

	return ts.tv_sec + ts.tv_nsec / 1000000000.0;
	}

double curThreadClock(void)
	{
	timespec ts;

	clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts); // Works on Linux

	return ts.tv_sec + ts.tv_nsec / 1000000000.0;
	}

std::string currentTimeAsString()
    {
    timeval tv;
    if (gettimeofday(&tv, 0) != 0)
        return std::string();

    tm* timeinfo = localtime(&tv.tv_sec);
    char buffer[80];
    snprintf(
            buffer,
            sizeof(buffer),
            "%04d-%02d-%02d %02d:%02d:%02d,%03d",
            timeinfo->tm_year + 1900,
            timeinfo->tm_mon + 1,
            timeinfo->tm_mday,
            timeinfo->tm_hour,
            timeinfo->tm_min,
            timeinfo->tm_sec,
            (int)tv.tv_usec/1000
           );
    return std::string(buffer);
    }

#endif // BSA_PLATFORM_WINDOWS


