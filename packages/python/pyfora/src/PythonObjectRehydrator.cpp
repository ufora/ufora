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
        const PyObjectPtr& purePythonClassMapping,
        bool allowUserCodeModuleLevelLookups)
    : mPureImplementationMappings(purePythonClassMapping),
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
    PyObjectPtr PythonObjectRehydratorHelpersModule = PyObjectPtr::unincremented(
        PyImport_ImportModule(
            "pyfora.PythonObjectRehydratorHelpers"
            ));
    if (PythonObjectRehydratorHelpersModule == nullptr) {
        throw std::runtime_error(
            "py error while creating a (cpp) PythonObjectRehydrator: " +
            PyObjectUtils::exc_string()
            );
        }
    
    mNoConversionFunc = PyObjectPtr::unincremented(PyObject_GetAttrString(
            PythonObjectRehydratorHelpersModule.get(),
            "noConversion"
            ));

    if (mNoConversionFunc == nullptr) {
        throw std::runtime_error(
            "error creating a (cpp) PythonObjectRehydrator: " +
            PyObjectUtils::exc_string()
            );        
        }
    }


void PythonObjectRehydrator::_initPurePythonObjectRehydratorHelpers(
        const PyObjectPtr& purePythonClassMapping,
        bool allowUserCodeModuleLevelLookups
        )
    {
    PyObjectPtr PurePythonObjectRehydratorHelpersModule = 
        PyObjectPtr::unincremented(
            PyImport_ImportModule(
                "pyfora.PythonObjectRehydratorHelpers"
                ));
    if (PurePythonObjectRehydratorHelpersModule == nullptr) {
        throw std::runtime_error(
            "py error while creating a (cpp) PythonObjectRehydrator: " +
            PyObjectUtils::exc_string()
            );
        }
    
    PyObjectPtr PurePythonObjectRehydratorHelpersClass = 
        PyObjectPtr::unincremented(
            PyObject_GetAttrString(
                PurePythonObjectRehydratorHelpersModule.get(),
                "PythonObjectRehydratorHelpers"
                ));
    if (PurePythonObjectRehydratorHelpersClass == nullptr) {
        throw std::runtime_error(
            "py error while creating a (cpp) PythonObjectRehydrator: " +
            PyObjectUtils::exc_string()
            );        
        }

    mPurePythonObjectRehydratorHelpers = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            PurePythonObjectRehydratorHelpersClass.get(),
            purePythonClassMapping.get(),
            allowUserCodeModuleLevelLookups ? Py_True : Py_False,
            nullptr
            ));

    if (mPurePythonObjectRehydratorHelpers == nullptr) {
        throw std::runtime_error(
            "py error in PythonObjectRehydrator::_initPurePythonObjectRehydratorHelpers: " +
            PyObjectUtils::exc_string()
            );
        }
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
        mNoConversionFunc.get()
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
        mNoConversionFunc.get()
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
    PyObjectPtr pyLineNumber = PyObjectPtr::unincremented(
        PyInt_FromLong(linenumber));
    if (pyLineNumber == nullptr) {
        return nullptr;
        }

    PyObjectPtr classObjectFromFileFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPurePythonObjectRehydratorHelpers.get(),
            "classObjectFromFile"
            ));
    if (classObjectFromFileFun == nullptr) {
        return nullptr;
        }

    return PyObject_CallFunctionObjArgs(
        classObjectFromFileFun.get(),
        pyFileDescription,
        pyLineNumber.get(),
        convertedMembers,
        nullptr
        );
    }


PyObject* PythonObjectRehydrator::instantiateFunction(
        PyObject* pyFileDescription,
        int32_t linenumber,
        PyObject* convertedMembers
        )
    {
    PyObjectPtr pyLineNumber = PyObjectPtr::unincremented(
        PyInt_FromLong(linenumber));
    if (pyLineNumber == nullptr) {
        return nullptr;
        }

    PyObjectPtr functionFromFileFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPurePythonObjectRehydratorHelpers.get(),
            "instantiateFunctionFromFile"
            ));
    if (functionFromFileFun == nullptr) {
        return nullptr;
        }

    return PyObject_CallFunctionObjArgs(
        functionFromFileFun.get(),
        pyFileDescription,
        pyLineNumber.get(),
        convertedMembers,
        nullptr
        );
    }


PyObject* PythonObjectRehydrator::instantiateClass(
        PyObject* classObject,
        PyObject* membersDict
        )
    {
    PyObjectPtr methodName = PyObjectPtr::unincremented(
        PyString_FromString("instantiateClass"));
    if (methodName == nullptr) {
        return nullptr;
        }
    
    return PyObject_CallMethodObjArgs(
        mPurePythonObjectRehydratorHelpers.get(),
        methodName.get(),
        classObject,
        membersDict,
        nullptr
        );
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
