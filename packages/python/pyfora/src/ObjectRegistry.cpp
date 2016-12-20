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
#include "ObjectRegistry.hpp"
#include "PyObjectUtils.hpp"
#include "TypeDescriptions/BuiltinExceptionInstanceTypeDescription.hpp"
#include "TypeDescriptions/ClassTypeDescription.hpp"
#include "TypeDescriptions/ClassInstanceTypeDescription.hpp"
#include "TypeDescriptions/DictTypeDescription.hpp"
#include "TypeDescriptions/FileTypeDescription.hpp"
#include "TypeDescriptions/FunctionTypeDescription.hpp"
#include "TypeDescriptions/InstanceMethodTypeDescription.hpp"
#include "TypeDescriptions/ListTypeDescription.hpp"
#include "TypeDescriptions/NamedSingletonTypeDescription.hpp"
#include "TypeDescriptions/PackedHomogenousDataTypeDescription.hpp"
#include "TypeDescriptions/PrimitiveTypeDescription.hpp"
#include "TypeDescriptions/PyAbortExceptionTypeDescription.hpp"
#include "TypeDescriptions/RemotePythonObjectTypeDescription.hpp"
#include "TypeDescriptions/StackTraceTypeDescription.hpp"
#include "TypeDescriptions/TupleTypeDescription.hpp"
#include "TypeDescriptions/TypeDescription.hpp"
#include "TypeDescriptions/UnconvertibleTypeDescription.hpp"
#include "TypeDescriptions/UnresolvedSymbolTypeDescription.hpp"

#include <sstream>
#include <stdexcept>


std::shared_ptr<TypeDescription> ObjectRegistry::getDefinition(int64_t objectId) const
    {
    auto it = mObjectIdToObjectDefinition.find(objectId);

    if (it != mObjectIdToObjectDefinition.end()) {
        return it->second;
        }

    std::ostringstream err;
    err << "couldn't find objectId ";
    err << objectId;

    throw std::runtime_error(err.str());
    }


void ObjectRegistry::definePrimitive(int64_t objectId, PyObject* primitive)
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(new PrimitiveTypeDescription(primitive));
    }


void ObjectRegistry::defineTuple(
        int64_t objectId,
        const std::vector<int64_t>& objectIds
        )
    {
    mObjectIdToObjectDefinition[objectId] = 
        std::shared_ptr<TypeDescription>(new TupleTypeDescription(objectIds));
    }


void ObjectRegistry::definePackedHomogenousData(
        int64_t objectId,
        PyObject* dtype,
        const std::string& packedBytes
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new PackedHomogenousDataTypeDescription(
                dtype,
                packedBytes)
            );
    }


void ObjectRegistry::defineList(
        int64_t objectId,
        const std::vector<int64_t>& objectIds
        )
    {
    mObjectIdToObjectDefinition[objectId] = 
        std::shared_ptr<TypeDescription>(
            new ListTypeDescription(objectIds)
            );
    }


void ObjectRegistry::defineDict(
        int64_t objectId,
        const std::vector<int64_t>& keyIds,
        const std::vector<int64_t>& valueIds
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new DictTypeDescription(keyIds, valueIds)
            );
    }


void ObjectRegistry::defineNamedSingleton(
        int64_t objectId,
        const std::string& name
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new NamedSingletonTypeDescription(name)
            );
    }


void ObjectRegistry::defineFunction(
        int64_t objectId,
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new FunctionTypeDescription(
                sourceFileId,
                linenumber,
                freeVariableResolutions
                )
            );
    }


void ObjectRegistry::defineFile(
        int64_t objectId,
        const std::string& path,
        const std::string& text
        )
    {
    mObjectIdToObjectDefinition[objectId] = 
        std::shared_ptr<TypeDescription>(
            new FileTypeDescription(path, text)
            );
    }


void ObjectRegistry::defineClass(
        int64_t objectId,
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions,
        const std::vector<int64_t>& baseClassIds
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new ClassTypeDescription(
                sourceFileId,
                linenumber,
                freeVariableResolutions,
                baseClassIds
                )
            );
    }


void ObjectRegistry::defineClassInstance(
        int64_t objectId,
        int64_t classId,
        const std::map<std::string, int64_t>& classMembers
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new ClassInstanceTypeDescription(
                classId,
                classMembers
                )
            );
    }


void ObjectRegistry::defineUnconvertible(
        int64_t objectId,
        PyObject* stringTupleOrNone
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new UnconvertibleTypeDescription(
                stringTupleOrNone
                )
            );
    }


void ObjectRegistry::defineUnresolvedSymbol(
        int64_t objectId,
        const std::string& varname,
        int64_t lineno,
        int64_t col_offset
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new UnresolvedSymbolTypeDescription(
                varname,
                lineno,
                col_offset
                )
            );
    }


void ObjectRegistry::definePyAbortException(
        int64_t objectId,
        const std::string& typeName,
        int64_t argsId
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new PyAbortExceptionTypeDescription(
                typeName,
                argsId
                )
            );
    }


void ObjectRegistry::defineStacktrace(
        int64_t objectId,
        PyObject* stackTraceAsJson
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new StackTraceTypeDescription(
                stackTraceAsJson
                )
            );
    }


void ObjectRegistry::defineRemotePythonObject(
        int64_t objectId,
        PyObject* pyObject
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new RemotePythonObjectTypeDescription(pyObject)
            );
    }


void ObjectRegistry::defineBuiltinExceptionInstance(
        int64_t objectId,
        const std::string& typeName,
        int64_t argsId
        )
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new BuiltinExceptionInstanceTypeDescription(
                typeName,
                argsId
                )
            );
    }


void ObjectRegistry::defineInstanceMethod(
        int64_t objectId,
        int64_t instanceId,
        const std::string& methodName)
    {
    mObjectIdToObjectDefinition[objectId] =
        std::shared_ptr<TypeDescription>(
            new InstanceMethodTypeDescription(
                instanceId,
                methodName
                )
            );
    }


void ObjectRegistry::defineWithBlock(
        int64_t objectId,
        PyObject* resolutions,
        int64_t sourceFileId,
        int32_t linenumber)
    {
    throw std::runtime_error("ObjectRegistry::defineWithBlock not implemented");
    }


std::string ObjectRegistry::str()
    {
    std::ostringstream oss;
    
    oss << "<ObjectRegistry object at "
        << (void*) this
        << ". objectIdToObjectDefinition = \n"
        ;
    for (const auto& p: mObjectIdToObjectDefinition) {
        oss << "\t" << p.first << ": " << p.second->toString() << "\n";
        }
    oss << "\n\t>";

    return oss.str();
    }
