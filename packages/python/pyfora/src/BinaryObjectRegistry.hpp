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

#include "BinaryObjectRegistryHelpers.hpp"
#include "Json.hpp"
#include "StringBuilder.hpp"


class FreeVariableMemberAccessChain;


class BinaryObjectRegistry {
public:
    constexpr static uint8_t CODE_NONE=1;
    constexpr static uint8_t CODE_INT=2;
    constexpr static uint8_t CODE_LONG=3;
    constexpr static uint8_t CODE_FLOAT=4;
    constexpr static uint8_t CODE_BOOL=5;
    constexpr static uint8_t CODE_STR=6;
    constexpr static uint8_t CODE_LIST_OF_PRIMITIVES=7;
    constexpr static uint8_t CODE_TUPLE=8;
    constexpr static uint8_t CODE_PACKED_HOMOGENOUS_DATA=9;
    constexpr static uint8_t CODE_LIST=10;
    constexpr static uint8_t CODE_FILE=11;
    constexpr static uint8_t CODE_DICT=12;
    constexpr static uint8_t CODE_REMOTE_PY_OBJECT=13;
    constexpr static uint8_t CODE_BUILTIN_EXCEPTION_INSTANCE=14;
    constexpr static uint8_t CODE_NAMED_SINGLETON=15;
    constexpr static uint8_t CODE_FUNCTION=16;
    constexpr static uint8_t CODE_CLASS=17;
    constexpr static uint8_t CODE_UNCONVERTIBLE=18;
    constexpr static uint8_t CODE_CLASS_INSTANCE=19;
    constexpr static uint8_t CODE_INSTANCE_METHOD=20;
    constexpr static uint8_t CODE_WITH_BLOCK=21;
    constexpr static uint8_t CODE_PY_ABORT_EXCEPTION=22;
    constexpr static uint8_t CODE_STACKTRACE_AS_JSON=23;

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
    Json mJsonModule;
    BinaryObjectRegistryHelpers mBinaryObjectRegisteryHelpers;

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


inline
int64_t BinaryObjectRegistry::allocateObject() {
    int64_t objectId = mNextObjectId;
    mNextObjectId++;
    return objectId;
    }


inline
void BinaryObjectRegistry::_writePrimitive(bool b) {
    mStringBuilder.addByte(CODE_BOOL);
    mStringBuilder.addByte(b ? 1 : 0);
    }


inline
void BinaryObjectRegistry::_writePrimitive(int64_t i) {
    mStringBuilder.addByte(CODE_INT);
    mStringBuilder.addInt64(i);
    }


inline
void BinaryObjectRegistry::_writePrimitive(double d) {
    mStringBuilder.addByte(CODE_FLOAT);
    mStringBuilder.addFloat64(d);
    }


inline
void BinaryObjectRegistry::_writePrimitive(const std::string& s) {
    mStringBuilder.addByte(CODE_STR);
    mStringBuilder.addString(s);
    }


inline
void BinaryObjectRegistry::defineTuple(int64_t objectId,
                                       const std::vector<int64_t>& memberIds)
    {
    defineTuple(objectId,
                &memberIds[0],
                memberIds.size());
    }

    
inline
void BinaryObjectRegistry::defineTuple(int64_t objectId,
                                       const int64_t* memberIds,
                                       uint64_t nMemberIds)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_TUPLE);
    mStringBuilder.addInt64s(memberIds, nMemberIds);
    }


inline
void BinaryObjectRegistry::defineList(int64_t objectId,
                                      const std::vector<int64_t>& memberIds)
    {
    defineList(objectId,
               &memberIds[0],
               memberIds.size());
    }

    
inline
void BinaryObjectRegistry::defineList(int64_t objectId,
                                      const int64_t* memberIds,
                                      uint64_t nMemberIds)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_LIST);
    mStringBuilder.addInt64s(memberIds, nMemberIds);
    }


inline
void BinaryObjectRegistry::defineFile(int64_t objectId,
                                      const std::string& text,
                                      const std::string& path)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_FILE);
    mStringBuilder.addString(path);
    mStringBuilder.addString(text);
    }


inline
void BinaryObjectRegistry::defineDict(int64_t objectId,
                                      const std::vector<int64_t>& keyIds,
                                      const std::vector<int64_t>& valueIds)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_DICT);
    mStringBuilder.addInt64s(keyIds);
    mStringBuilder.addInt64s(valueIds);
    }


inline
void BinaryObjectRegistry::defineBuiltinExceptionInstance(
        int64_t objectId,
        const std::string& typeName,
        int64_t argsId)
    {
    defineBuiltinExceptionInstance(
        objectId,
        typeName.data(),
        typeName.size(),
        argsId);
    }


inline
void BinaryObjectRegistry::defineBuiltinExceptionInstance(
        int64_t objectId,
        const char* typeName,
        uint64_t typeNameSize,
        int64_t argsId)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_BUILTIN_EXCEPTION_INSTANCE);
    mStringBuilder.addString(typeName, typeNameSize);
    mStringBuilder.addInt64(argsId);
    }


inline
void BinaryObjectRegistry::defineNamedSingleton(
        int64_t objectId,
        const std::string& singletonName)
    {
    defineNamedSingleton(objectId, singletonName.data(), singletonName.size());
    }


inline
void BinaryObjectRegistry::defineNamedSingleton(
        int64_t objectId,
        const char* singletonName,
        uint64_t singletonNameSize)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_NAMED_SINGLETON);
    mStringBuilder.addString(singletonName, singletonNameSize);
    }


inline
void BinaryObjectRegistry::defineStacktrace(
        int64_t objectId,
        const PyObject* stacktraceAsJson)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_STACKTRACE_AS_JSON);
    mStringBuilder.addString(mJsonModule.dumps(stacktraceAsJson));
    }
