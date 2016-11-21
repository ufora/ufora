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
#include "ModuleLevelObjectIndex.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


ModuleLevelObjectIndex::ModuleLevelObjectIndex()
    : mModuleLevelObjectIndexSingleton(nullptr)
    {
    PyObject* moduleLevelObjectIndexModule = PyImport_ImportModule(
        "pyfora.ModuleLevelObjectIndex"
        );
    if (moduleLevelObjectIndexModule == nullptr) {
        throw std::runtime_error(
            "error getting pyfora.ModuleLevelObjectIndex "
            "in ModuleLevelObjectIndex::get():\n" +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* moduleLevelObjectIndexClass = PyObject_GetAttrString(
        moduleLevelObjectIndexModule,
        "ModuleLevelObjectIndex"
        );
    if (moduleLevelObjectIndexClass == nullptr) {
        Py_DECREF(moduleLevelObjectIndexModule);
        throw std::runtime_error(
            "error getting ModuleLevelObjectIndex.ModuleLevelObjectIndex "
            "in ModuleLevelObjectIndex::get():\n" +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* singletonFunc = PyObject_GetAttrString(
        moduleLevelObjectIndexClass,
        "singleton"
        );
    if (singletonFunc == nullptr) {
        Py_DECREF(moduleLevelObjectIndexClass);
        Py_DECREF(moduleLevelObjectIndexModule);
        throw std::runtime_error(
            "error getting ModuleLevelObjectIndex.singleton "
            "in ModuleLevelObjectIndex::get():\n" +
            PyObjectUtils::exc_string()
            );
        }

    mModuleLevelObjectIndexSingleton = PyObject_CallFunctionObjArgs(
        singletonFunc,
        nullptr
        );

    Py_DECREF(singletonFunc);
    Py_DECREF(moduleLevelObjectIndexClass);
    Py_DECREF(moduleLevelObjectIndexModule);

    if (mModuleLevelObjectIndexSingleton == nullptr) {
        throw std::runtime_error(
            "error getting ModuleLevelObjectIndex.singleton "
            "in ModuleLevelObjectIndex::get():\n" +
            PyObjectUtils::exc_string()
            );
        }
    }


ModuleLevelObjectIndex::ModuleLevelObjectIndex(
        const ModuleLevelObjectIndex& other
        )
    : mModuleLevelObjectIndexSingleton(other.mModuleLevelObjectIndexSingleton)
    {
    Py_INCREF(mModuleLevelObjectIndexSingleton);
    }


ModuleLevelObjectIndex::~ModuleLevelObjectIndex()
    {
    Py_XDECREF(mModuleLevelObjectIndexSingleton);
    }


PyObject*
ModuleLevelObjectIndex::getPathToObject(const PyObject* pyObject) const
    {
    PyObject* getPathToObjectFun = PyObject_GetAttrString(
        mModuleLevelObjectIndexSingleton,
        "getPathToObject"
        );

    PyObject* tr =PyObject_CallFunctionObjArgs(
        getPathToObjectFun,
        pyObject,
        nullptr);
    
    Py_DECREF(getPathToObjectFun);

    return tr;
    }


PyObject*
ModuleLevelObjectIndex::getObjectFromPath(const PyObject* pyObject) const
    {
    PyObject* getObjectFromPathFun = PyObject_GetAttrString(
        mModuleLevelObjectIndexSingleton,
        "getObjectFromPath"
        );

    PyObject* tr =PyObject_CallFunctionObjArgs(
        getObjectFromPathFun,
        pyObject,
        nullptr);
    
    Py_DECREF(getObjectFromPathFun);

    return tr;
    }
