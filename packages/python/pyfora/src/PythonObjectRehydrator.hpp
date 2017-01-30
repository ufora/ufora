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
#include "PureImplementationMappings.hpp"
#include "core/PyObjectPtr.hpp"

#include <stdint.h>
#include <string>


class ObjectRegistry;
class PureImplementationMappings;


class PythonObjectRehydrator {
public:
    PythonObjectRehydrator(
        const PyObjectPtr& purePythonClassMapping,
        bool allowUserCodeModuleLevelLookups);

    PyObject* convertEncodedStringToPythonObject(
        const std::string& binarydata,
        int64_t root_id
        );

    PyObject* readFileDescriptorToPythonObject(
        int filedescriptor
        );

    PyObject* createClassObject(
        PyObject* pyFileDescription,
        int32_t linenumber,
        PyObject* convertedMembers
        );
    
    PyObject* instantiateClass(
        PyObject* classObject,
        PyObject* membersDict
        );

    PyObject* instantiateFunction(
        PyObject* pyFileDescription,
        int32_t linenumber,
        PyObject* convertedMembers
        );

    // this class is basically just a shared pointer to a PyObject*
    PureImplementationMappings pureImplementationMappings() const {
        return mPureImplementationMappings;
        }

    PyObject* invertPureClassInstanceIfNecessary(PyObject* instance);

private:
    PythonObjectRehydrator(const PythonObjectRehydrator&) = delete;
    void operator=(const PythonObjectRehydrator&) = delete;

    PyObject* convertObjectDefinitionsToPythonObject(
        const ObjectRegistry& r,
        int64_t root_id
        );

    void _initNoConversionFunc();
    void _initPurePythonObjectRehydratorHelpers(
        const PyObjectPtr& purePythonClassMapping,
        bool allowUserCodeModuleLevelLookups
        );

    PyObjectPtr mNoConversionFunc;
    PureImplementationMappings mPureImplementationMappings;
    PyObjectPtr mPurePythonObjectRehydratorHelpers;
    ModuleLevelObjectIndex mModuleLevelObjectIndex;
};
