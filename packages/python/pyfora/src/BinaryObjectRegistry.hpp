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

#include <map>
#include <set>
#include <stdint.h>
#include <string>

#include "StringBuilder.hpp"


class FreeVariableMemberAccessChain;


class BinaryObjectRegistry {
public:
    const static uint8_t CODE_NONE=1;
    const static uint8_t CODE_INT=2;
    const static uint8_t CODE_LONG=3;
    const static uint8_t CODE_FLOAT=4;
    const static uint8_t CODE_BOOL=5;
    const static uint8_t CODE_STR=6;
    const static uint8_t CODE_LIST_OF_PRIMITIVES=7;
    const static uint8_t CODE_TUPLE=8;
    const static uint8_t CODE_PACKED_HOMOGENOUS_DATA=9;
    const static uint8_t CODE_LIST=10;
    const static uint8_t CODE_FILE=11;
    const static uint8_t CODE_DICT=12;
    const static uint8_t CODE_REMOTE_PY_OBJECT=13;
    const static uint8_t CODE_BUILTIN_EXCEPTION_INSTANCE=14;
    const static uint8_t CODE_NAMED_SINGLETON=15;
    const static uint8_t CODE_FUNCTION=16;
    const static uint8_t CODE_CLASS=17;
    const static uint8_t CODE_UNCONVERTIBLE=18;
    const static uint8_t CODE_CLASS_INSTANCE=19;
    const static uint8_t CODE_INSTANCE_METHOD=20;
    const static uint8_t CODE_WITH_BLOCK=21;
    const static uint8_t CODE_PY_ABORT_EXCEPTION=22;
    const static uint8_t CODE_STACKTRACE_AS_JSON=23;

public:
    BinaryObjectRegistry();

    uint64_t bytecount() const {
        return mStringBuilder.bytecount();
        }

    std::string str() const {
        return mStringBuilder.str();
        }

    void clear() {
        mStringBuilder.clear();
        }
        
    int64_t allocateObject();

    template<class T>
    void definePrimitive(uint64_t objectId, const T& t) {
        mStringBuilder.addInt64(objectId);
        _writePrimitive(t);
        }

    void defineEndOfStream();
    void defineTuple(int64_t objectId,
                     const std::vector<int64_t>& memberIds);
    void defineTuple(int64_t objectId,
                     const int64_t* memberIds,
                     uint64_t nMemberIds);
    void defineList(int64_t objectId,
                    const std::vector<int64_t>& memberIds);
    void defineList(int64_t objectId,
                    const int64_t* memberIds,
                    uint64_t nMemberIds);
    void defineFile(int64_t objectId,
                    const std::string& text,
                    const std::string& path);
    void defineDict(int64_t objectId,
                    const std::vector<int64_t>& keyIds,
                    const std::vector<int64_t>& valueIds);
    void defineRemotePythonObject(int64_t objectId,
                                  const PyObject* computedValueArg);
    void defineBuiltinExceptionInstance(int64_t objectId,
                                        const std::string& typeName,
                                        int64_t argsId);
    void defineBuiltinExceptionInstance(int64_t objectId,
                                        const char* typeName,
                                        uint64_t typeNameSize,
                                        int64_t argsId);
    void defineNamedSingleton(int64_t objectId,
                              const std::string& singletonName);
    void defineNamedSingleton(int64_t objectId,
                              const char* singletonName,
                              uint64_t singletonNameSize);

    template<class T>
    void defineFunction(
            int64_t objectId,
            int64_t sourceFileId,
            int32_t linenumber,
            const T& chainToId
            )
        {
        mStringBuilder.addInt64(objectId);
        mStringBuilder.addByte(CODE_FUNCTION);
        mStringBuilder.addInt64(sourceFileId);
        mStringBuilder.addInt32(linenumber);
        _writeFreeVariableResolutions(chainToId);
        }

    template<class T>
    void defineClass(
            int64_t objectId,
            int64_t sourceFileId,
            int32_t lineNumber,
            const T& chainToId,
            const std::vector<int64_t> baseClassIds
            )
        {
        mStringBuilder.addInt64(objectId);
        mStringBuilder.addByte(CODE_CLASS);
        mStringBuilder.addInt64(sourceFileId);
        mStringBuilder.addInt32(lineNumber);
        _writeFreeVariableResolutions(chainToId);
        mStringBuilder.addInt64s(baseClassIds);
        }

    void defineUnconvertible(int64_t objectId, const PyObject* modulePathOrNone);
    void defineClassInstance(
        int64_t objectId,
        int64_t classId,
        const std::map<std::string, int64_t>& classMemberNameToClassMemberId);
    void defineInstanceMethod(int64_t objectId,
                              int64_t instanceId,
                              const std::string& methodName);

    template<class T>
    void defineWithBlock(
            int64_t objectId,
            const T& chainToId,
            int64_t sourceFileId,
            int32_t lineNumber)
        {
        mStringBuilder.addInt64(objectId);
        mStringBuilder.addByte(CODE_WITH_BLOCK);
        _writeFreeVariableResolutions(chainToId);
        mStringBuilder.addInt64(sourceFileId);
        mStringBuilder.addInt32(lineNumber);
        }

    void definePyAbortException(int64_t objectId,
                                const std::string& typeName,
                                int64_t argsId);
    void defineStacktrace(int64_t objectId,
                          const PyObject* stacktraceAsJson);
    void definePackedHomogenousData(int64_t objectId,
                                    PyObject* val);

    bool isUnconvertible(int64_t classId) {
        return mUnconvertibleIndices.find(classId) != mUnconvertibleIndices.end();
        }

private:
    StringBuilder mStringBuilder;
    int64_t mNextObjectId;
    std::set<int64_t> mUnconvertibleIndices;

    void _writePrimitive(bool b);
    void _writePrimitive(int64_t l);
    void _writePrimitive(double d);
    void _writePrimitive(const std::string& s);
    void _writePrimitive(PyObject* pyObject);

    void _writeDTypeElement(PyObject* val);

    void _writeFreeVariableResolutions(
        const std::map<FreeVariableMemberAccessChain, int64_t>& chainToId
        );

    void _writeFreeVariableResolutions(PyObject* chainToId);

    std::string _computedValueDataString(const PyObject* computedValueArg) const;

    };
