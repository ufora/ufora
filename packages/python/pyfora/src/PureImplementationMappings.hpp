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
  A refcounted version of (pure) python PureImplementationMappings
 */
class PureImplementationMappings {
public:
    explicit PureImplementationMappings(PyObject* pyPureImplementationMappings);

    PureImplementationMappings(const PureImplementationMappings&);

    ~PureImplementationMappings();
    
    bool canMap(const PyObject* pyObject);
    bool canInvertInstancesOf(const PyObject* pyObject);
    bool canInvert(const PyObject* pyObject);

    PyObject* mappableInstanceToPure(const PyObject* pyObject);
    PyObject* pureInstanceToMappable(const PyObject* instance);

private:
    PureImplementationMappings& operator=(const PureImplementationMappings&) = delete;

    PyObject* mPyPureImplementationMappings;
};
