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


class ModuleLevelObjectIndex {
public:
    static ModuleLevelObjectIndex get();        

    ModuleLevelObjectIndex(const ModuleLevelObjectIndex&);

    ~ModuleLevelObjectIndex();

    PyObject* getObjectFromPath(const PyObject* path) const;
    PyObject* getPathToObject(const PyObject* obj) const;

private:
    // STEALS a reference to moduleLevelObjectIndexSingleton.
    // In other words, this class does not incref this arg,
    // but does decref it on destruction
    explicit ModuleLevelObjectIndex(
        PyObject* moduleLevelObjectIndexSingleton
        );

    void operator=(const ModuleLevelObjectIndex&) = delete;
    
    PyObject* mModuleLevelObjectIndexSingleton;
    };
