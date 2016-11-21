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
#include "PythonObjectRehydrator.hpp"

#include "IRToPythonConverter.hpp"
#include "ObjectRegistry.hpp"
#include "PyObjectUtils.hpp"
#include "serialization/BinaryObjectRegistryDeserializer.hpp"
#include "serialization/DeserializerBase.hpp"
#include "serialization/FileDescriptorDeserializer.hpp"
#include "serialization/StringDeserializer.hpp"

#include <memory>
#include <stdexcept>


PythonObjectRehydrator::PythonObjectRehydrator(
        PyObject* purePythonClassMapping,
        bool allowUserCodeModuleLevelLookups)
    : mNoConversionFunc(nullptr),
      mPureImplementationMappings(purePythonClassMapping),
      mPurePythonObjectRehydratorHelpers(nullptr),
      mModuleLevelObjectIndex(ModuleLevelObjectIndex())
    {
    _initNoConversionFunc();
    _initPurePythonObjectRehydratorHelpers(
        purePythonClassMapping,
        allowUserCodeModuleLevelLookups
        );
    }


void PythonObjectRehydrator::_initNoConversionFunc()
    {
    PyObject* PythonObjectRehydratorHelpersModule = PyImport_ImportModule(
        "pyfora.PythonObjectRehydratorHelpers"
        );
    if (PythonObjectRehydratorHelpersModule == nullptr) {
        throw std::runtime_error(
            "py error while creating a (cpp) PythonObjectRehydrator: " +
            PyObjectUtils::exc_string()
            );
        }
    
    mNoConversionFunc = PyObject_GetAttrString(
        PythonObjectRehydratorHelpersModule,
        "noConversion"
        );
    
    Py_DECREF(PythonObjectRehydratorHelpersModule);

    if (mNoConversionFunc == nullptr) {
        throw std::runtime_error(
            "error creating a (cpp) PythonObjectRehydrator: " +
            PyObjectUtils::exc_string()
            );        
        }
    }


void PythonObjectRehydrator::_initPurePythonObjectRehydratorHelpers(
        PyObject* purePythonClassMapping,
        bool allowUserCodeModuleLevelLookups
        )
    {
    PyObject* PurePythonObjectRehydratorHelpersModule = PyImport_ImportModule(
        "pyfora.PythonObjectRehydratorHelpers"
        );
    if (PurePythonObjectRehydratorHelpersModule == nullptr) {
        throw std::runtime_error(
            "py error while creating a (cpp) PythonObjectRehydrator: " +
            PyObjectUtils::exc_string()
            );
        }
    
    PyObject* PurePythonObjectRehydratorHelpersClass = PyObject_GetAttrString(
        PurePythonObjectRehydratorHelpersModule,
        "PythonObjectRehydratorHelpers"
        );
    Py_DECREF(PurePythonObjectRehydratorHelpersModule);
    if (PurePythonObjectRehydratorHelpersClass == nullptr) {
        throw std::runtime_error(
            "py error while creating a (cpp) PythonObjectRehydrator: " +
            PyObjectUtils::exc_string()
            );        
        }

    mPurePythonObjectRehydratorHelpers = PyObject_CallFunctionObjArgs(
        PurePythonObjectRehydratorHelpersClass,
        purePythonClassMapping,
        allowUserCodeModuleLevelLookups ? Py_True : Py_False,
        nullptr
        );

    Py_DECREF(PurePythonObjectRehydratorHelpersClass);

    if (mPurePythonObjectRehydratorHelpers == nullptr) {
        throw std::runtime_error(
            "py error in PythonObjectRehydrator::_initPurePythonObjectRehydratorHelpers: " +
            PyObjectUtils::exc_string()
            );
        }
    }


PythonObjectRehydrator::~PythonObjectRehydrator()
    {
    Py_XDECREF(mPurePythonObjectRehydratorHelpers);
    Py_XDECREF(mNoConversionFunc);
    }


PyObject* PythonObjectRehydrator::readFileDescriptorToPythonObject(
        int filedescriptor
        )
    {
    ObjectRegistry registry;
    std::shared_ptr<Deserializer> deserializer(
        new FileDescriptorDeserializer(filedescriptor)
        );
    BinaryObjectRegistryDeserializer::deserializeFromStream(
        deserializer,
        registry,
        mNoConversionFunc
        );
    
    int64_t root_id = deserializer->readInt64();

    return convertObjectDefinitionsToPythonObject(registry, root_id);
    }


PyObject* PythonObjectRehydrator::convertEncodedStringToPythonObject(
        const std::string& binarydata,
        int64_t root_id
        )
    {
    ObjectRegistry registry;
    std::shared_ptr<Deserializer> deserializer(
        new StringDeserializer(binarydata)
        );
    BinaryObjectRegistryDeserializer::deserializeFromStream(
        deserializer,
        registry,
        mNoConversionFunc
        );

    return convertObjectDefinitionsToPythonObject(registry, root_id);
    }


PyObject* PythonObjectRehydrator::convertObjectDefinitionsToPythonObject(
        const ObjectRegistry& registry,
        int64_t root_id
        )
    {
    std::map<int64_t, PyObject*> converted;
    IRToPythonConverter converter(*this,
                                  registry,
                                  converted,
                                  mModuleLevelObjectIndex);

    PyObject* tr = converter.convert(root_id);

    for (const auto& p: converted) {
        Py_DECREF(p.second);
        }

    return tr;
    }


PyObject* PythonObjectRehydrator::createClassObject(
        PyObject* pyFileDescription,
        int32_t linenumber,
        PyObject* convertedMembers
        )
    {
    PyObject* pyLineNumber = PyInt_FromLong(linenumber);
    if (pyLineNumber == nullptr) {
        return nullptr;
        }

    PyObject* classObjectFromFileFun = PyObject_GetAttrString(
        mPurePythonObjectRehydratorHelpers,
        "classObjectFromFile"
        );
    if (classObjectFromFileFun == nullptr) {
        Py_DECREF(pyLineNumber);
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        classObjectFromFileFun,
        pyFileDescription,
        pyLineNumber,
        convertedMembers,
        nullptr
        );

    Py_DECREF(classObjectFromFileFun);
    Py_DECREF(pyLineNumber);

    return tr;
    }


PyObject* PythonObjectRehydrator::instantiateFunction(
        PyObject* pyFileDescription,
        int32_t linenumber,
        PyObject* convertedMembers
        )
    {
    PyObject* pyLineNumber = PyInt_FromLong(linenumber);
    if (pyLineNumber == nullptr) {
        return nullptr;
        }

    PyObject* fileFromFileFun = PyObject_GetAttrString(
        mPurePythonObjectRehydratorHelpers,
        "instantiateFunctionFromFile"
        );
    if (fileFromFileFun == nullptr) {
        Py_DECREF(pyLineNumber);
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        fileFromFileFun,
        pyFileDescription,
        pyLineNumber,
        convertedMembers,
        nullptr
        );

    Py_DECREF(fileFromFileFun);
    Py_DECREF(pyLineNumber);

    return tr;
    }


PyObject* PythonObjectRehydrator::instantiateClass(
        PyObject* classObject,
        PyObject* membersDict
        )
    {
    PyObject* methodName = PyString_FromString("instantiateClass");
    if (methodName == nullptr) {
        return nullptr;
        }
    
    PyObject* tr = PyObject_CallMethodObjArgs(
        mPurePythonObjectRehydratorHelpers,
        methodName,
        classObject,
        membersDict,
        nullptr
        );

    Py_DECREF(methodName);

    return tr;
    }


PyObject*
PythonObjectRehydrator::invertPureClassInstanceIfNecessary(PyObject* instance)
    {
    if (pureImplementationMappings().canInvert(instance)) {
        return pureImplementationMappings().pureInstanceToMappable(instance);
        }

    Py_INCREF(instance);

    return instance;
    }
