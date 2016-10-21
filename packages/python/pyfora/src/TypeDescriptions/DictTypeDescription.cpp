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
#include "../IRToPythonConverter.hpp"
#include "DictTypeDescription.hpp"

#include <stdexcept>


DictTypeDescription::DictTypeDescription(
        const std::vector<int64_t>& keyIds,
        const std::vector<int64_t>& valueIds
        )
    : mKeyIds(keyIds),
      mValueIds(valueIds)
    {
    }


DictTypeDescription::~DictTypeDescription()
    {
    }


PyObject* DictTypeDescription::transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy
        )
    {
    size_type ct = mKeyIds.size();
    if (ct != mValueIds.size()) {
        throw std::runtime_error(
            "keyIds and valueIds must have the same length"
            );
        }

    PyObject* tr = PyDict_New();
    if (tr == nullptr) {
        return nullptr;
        }

    for (size_type ix = 0; ix < ct; ++ix) {
        PyObject* key = c.convert(mKeyIds[ix]);
        if (key == nullptr) {
            Py_DECREF(tr);
            return nullptr;
            }

        PyObject* value = c.convert(mValueIds[ix]);
        if (value == nullptr) {
            Py_DECREF(key);
            Py_DECREF(tr);
            return nullptr;
            }
        
        int retcode = PyDict_SetItem(tr, key, value);

        if (retcode != 0) {
            Py_DECREF(value);
            Py_DECREF(key);
            Py_DECREF(tr);
            return nullptr;
            }
        }

    return tr;
    }
