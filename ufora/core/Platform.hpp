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
#ifndef BSA_Platform_hpp_
#define BSA_Platform_hpp_


#if defined(__linux__) || defined(BSA_IS_LINUX)
#define BSA_PLATFORM_LINUX 1

#elif defined(_WIN32) || defined(_WIN64)
#define BSA_PLATFORM_WINDOWS 1

#elif defined(__APPLE__)
#define BSA_PLATFORM_APPLE 1

#endif


#endif

