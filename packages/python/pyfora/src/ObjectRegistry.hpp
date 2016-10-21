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

#include "TypeDescriptions/TypeDescription.hpp"

#include <map>
#include <memory>
#include <stdint.h>
#include <string>
#include <vector>


class ObjectRegistry {
public:
    ObjectRegistry() 
        {
        }

    void definePrimitive(int64_t, PyObject* primitive);
    void defineTuple(
        int64_t objectId,
        const std::vector<int64_t>& objectIds);

    void definePackedHomogenousData(
        int64_t objectId,
        PyObject* dtype,
        const std::string& packedBytes);
    void defineList(
        int64_t objectId,
        const std::vector<int64_t>& objectIds);
    void defineFile(
        int64_t objectId,
        const std::string& path,
        const std::string& text);
    void defineDict(
        int64_t objectId,
        const std::vector<int64_t>& keyIds,
        const std::vector<int64_t>& valueIds);
    void defineRemotePythonObject(
        int64_t objectId,
        PyObject* pyObject);
    void defineBuiltinExceptionInstance(
        int64_t objectId,
        const std::string& typeName,
        int64_t argsId);
    void defineNamedSingleton(
        int64_t objectId,
        const std::string& singletonName);
    void defineFunction(
        int64_t objectId,
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions);
    void defineClass(
        int64_t objectId,
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions,
        const std::vector<int64_t>& baseClassIds);
    void defineUnconvertible(
        int64_t objectId,
        PyObject* stringTupleOrNone);
    void defineClassInstance(
        int64_t objectId,
        int64_t classId,
        const std::map<std::string, int64_t>& classMembers);
    void defineInstanceMethod(
        int64_t objectId,
        int64_t instanceId,
        const std::string& methodName);
    void defineWithBlock(
        int64_t objectId,
        PyObject* resolutions,
        int64_t sourceFileId,
        int32_t linenumber);
    void definePyAbortException(
        int64_t objectId,
        const std::string& typeName,
        int64_t argsId);
    void defineStacktrace(
        int64_t objectId,
        PyObject* stackTraceAsJson
        );

    std::shared_ptr<TypeDescription> getDefinition(int64_t objectId) const;

    std::string str();

private:
    std::map<int64_t, std::shared_ptr<TypeDescription>>
        mObjectIdToObjectDefinition;
};
