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
    {
    PyObjectPtr moduleLevelObjectIndexModule = PyObjectPtr::unincremented(
        PyImport_ImportModule(
            "pyfora.ModuleLevelObjectIndex"
            ));
    if (moduleLevelObjectIndexModule == nullptr) {
        throw std::runtime_error(
            "error getting pyfora.ModuleLevelObjectIndex "
            "in ModuleLevelObjectIndex::get():\n" +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr moduleLevelObjectIndexClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            moduleLevelObjectIndexModule.get(),
            "ModuleLevelObjectIndex"
            ));
    if (moduleLevelObjectIndexClass == nullptr) {
        throw std::runtime_error(
            "error getting ModuleLevelObjectIndex.ModuleLevelObjectIndex "
            "in ModuleLevelObjectIndex::get():\n" +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr singletonFunc = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            moduleLevelObjectIndexClass.get(),
            "singleton"
            ));
    if (singletonFunc == nullptr) {
        throw std::runtime_error(
            "error getting ModuleLevelObjectIndex.singleton "
            "in ModuleLevelObjectIndex::get():\n" +
            PyObjectUtils::exc_string()
            );
        }

    mModuleLevelObjectIndexSingleton = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            singletonFunc.get(),
            nullptr
            ));

    if (mModuleLevelObjectIndexSingleton == nullptr) {
        throw std::runtime_error(
            "error getting ModuleLevelObjectIndex.singleton "
            "in ModuleLevelObjectIndex::get():\n" +
            PyObjectUtils::exc_string()
            );
        }
    }


PyObject*
ModuleLevelObjectIndex::getPathToObject(const PyObject* pyObject) const
    {
    PyObjectPtr getPathToObjectFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mModuleLevelObjectIndexSingleton.get(),
            "getPathToObject"
            ));

    return PyObject_CallFunctionObjArgs(
        getPathToObjectFun.get(),
        pyObject,
        nullptr);
    }


PyObject*
ModuleLevelObjectIndex::getObjectFromPath(const PyObject* pyObject) const
    {
    PyObjectPtr getObjectFromPathFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mModuleLevelObjectIndexSingleton.get(),
            "getObjectFromPath"
            ));

    return PyObject_CallFunctionObjArgs(
        getObjectFromPathFun.get(),
        pyObject,
        nullptr);
    }
