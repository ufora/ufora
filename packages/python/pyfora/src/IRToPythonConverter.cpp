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
#include "IRToPythonConverter.hpp"
#include "ObjectRegistry.hpp"
#include "PyObjectUtils.hpp"
#include "PythonObjectRehydrator.hpp"

#include <sstream>
#include <stdexcept>


IRToPythonConverter::IRToPythonConverter(
        PythonObjectRehydrator& rehydrator,
        const ObjectRegistry& registry,
        std::map<int64_t, PyObject*>& converted,
        const ModuleLevelObjectIndex& moduleLevelObjectIndex
        ) :
    mRehydrator(rehydrator),
    mObjectRegistry(registry),
    mConverted(converted),
    mModuleLevelObjectIndex(moduleLevelObjectIndex)
    {
    }


PyObject* IRToPythonConverter::convert(
        int64_t objectId,
        bool retainHomogenousListsAsNumpy
        )
    {
        {
        auto it = mConverted.find(objectId);

        if (it != mConverted.end()) {
            PyObject* tr = mConverted[objectId];

            Py_INCREF(tr);

            return tr;
            }
        }

    PyObject* tr = mObjectRegistry.getDefinition(objectId)
        ->transform(*this, retainHomogenousListsAsNumpy);

    if (tr == nullptr) {
        return nullptr;
        }

    mConverted[objectId] = tr;

    Py_INCREF(tr);

    return tr;
    }


PyObject* IRToPythonConverter::convertDict(
        const std::map<std::string, int64_t> nameToId,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyObject* tr = PyDict_New();
    if (tr == nullptr) {
        return nullptr;
        }

    for (const auto& nameAndId: nameToId) {
        PyObject* convertedValue = convert(
            nameAndId.second,
            retainHomogenousListsAsNumpy
            );
        if (convertedValue == nullptr) {
            Py_DECREF(tr);
            return nullptr;
            }

        int retval = PyDict_SetItemString(
            tr,
            nameAndId.first.c_str(),
            convertedValue
            );
        
        Py_DECREF(convertedValue);

        if (retval < 0) {
            Py_DECREF(tr);
            return nullptr;
            }
        }

    return tr;
    }


PyObject* IRToPythonConverter::convertDict(
        PyObject* nameToId,
        bool retainHomogenousListsAsNumpy
        )
    {
    if (not PyDict_Check(nameToId)) {
        PyErr_SetString(
            PyExc_TypeError,
            "expected nameToId to be a dict in "
            "IRToPythonConverter::convertDict"
            );
        return nullptr;
        }

    PyObject* tr = PyDict_New();
    if (tr == nullptr) {
        return nullptr;
        }

    PyObject* key;
    PyObject* value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(nameToId, &pos, &key, &value))
        {
        if (not PyInt_Check(value)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected values in IRToPythonConverter::convertDict "
                "dict to all be ints"
                );
            return nullptr;
            }        
        int64_t objectId = PyInt_AS_LONG(value);

        PyObject* converted = convert(objectId, retainHomogenousListsAsNumpy);
        if (converted == nullptr) {
            std::ostringstream err;
            err << "error converting value in "
                << "IRToPythonConverter::convertDict. "
                << "objectId = " << objectId
                ;
            PyErr_SetString(
                PyExc_RuntimeError,
                err.str().c_str()
                );
            return nullptr;
            }

        int retcode = PyDict_SetItem(tr, key, converted);

        Py_DECREF(converted);

        if (retcode < 0) {
            Py_DECREF(tr);
            return nullptr;
            }
        }

    return tr;
    }


PyObject* IRToPythonConverter::getObjectFromPath(const PyObject* path) const
    {
    return mModuleLevelObjectIndex.getObjectFromPath(path);
    }


PyObject* IRToPythonConverter::getPathToObject(const PyObject* obj) const
    {
    return mModuleLevelObjectIndex.getPathToObject(obj);
    }
