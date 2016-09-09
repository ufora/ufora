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
// Apparently we need to include boost's python headers before anything from
// numpy to pass various python config parameters in preprocessor macro
// variables.
#include <boost/python.hpp>
#define PY_ARRAY_UNIQUE_SYMBOL bsa_numpy_array_API
// Note that we do NOT set the NO_IMPORT_ARRAY flag; this is the one
// translation unit where we will be using the import function.
#include <numpy/arrayobject.h>

// Note that if we're going to include other user headers, this must
// be done AFTER the above numpy include (since they may also include that
// file, but with different preprocessor options).
// (We could avoid this include altogether easily, but it's friendly to
// ensure that our declaration and our definition actually line up.
#include "NumpyArrays.hpp"

namespace { struct InitObject { InitObject() { import_array(); } }; }

void Ufora::numpy::initialize_numpy_arrays() {
    static InitObject o;
}

