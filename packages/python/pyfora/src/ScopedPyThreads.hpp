/***************************************************************************
   Copyright 2016 Ufora Inc.

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

#include <Python.h>

/*
  A scoped class for releasing the Python GIL

  ex:

  {
  ScopedPyThreads releaseTheGil
  // do stuff without GIL
  } // dtor reacquires the GIL

 */
class ScopedPyThreads {
public:
    ScopedPyThreads();
    ~ScopedPyThreads();
private:
    PyThreadState* mState;

    ScopedPyThreads(const ScopedPyThreads&) = delete;
    void operator=(const ScopedPyThreads&) = delete;
};
