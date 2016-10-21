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

#include "ModuleLevelObjectIndex.hpp"

#include <map>
#include <stdint.h>
#include <string>


class ObjectRegistry;
class PythonObjectRehydrator;

class IRToPythonConverter {
public:
    IRToPythonConverter(
        PythonObjectRehydrator& rehydrator,
        const ObjectRegistry& registry,
        std::map<int64_t, PyObject*>& converted,
        const ModuleLevelObjectIndex& moduleLevelObjectIndex
        );
    

    PyObject* convert(int64_t objectId,
                      bool retainHomogenousListsAsNumpy=false
                      );

    /*
      nameToId should be a dict: obj (strings right now) -> objectId,
      otherwise a TypeError is set, and nullptr is returned
     */
    PyObject* convertDict(PyObject* nameToId,
                          bool retainHomogenousListsAsNumpy=false);

    PyObject* convertDict(const std::map<std::string, int64_t> nameToId,
                          bool retainHomogenousListsAsNumpy=false);

    PythonObjectRehydrator& rehydrator() const {
        return mRehydrator;
        }

    PyObject* getObjectFromPath(const PyObject* path) const;
    PyObject* getPathToObject(const PyObject* obj) const;

private:
    PythonObjectRehydrator& mRehydrator;
    const ObjectRegistry& mObjectRegistry;
    std::map<int64_t, PyObject*>& mConverted;
    ModuleLevelObjectIndex mModuleLevelObjectIndex;

    IRToPythonConverter(const IRToPythonConverter&) = delete;
    void operator=(const IRToPythonConverter&) = delete;
};
