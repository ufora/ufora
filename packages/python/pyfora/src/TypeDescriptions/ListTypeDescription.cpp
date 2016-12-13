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
#include "ListTypeDescription.hpp"


ListTypeDescription::ListTypeDescription(const std::vector<int64_t>& memberIds)
    : mMemberIds(memberIds)
    {
    }


PyObject* ListTypeDescription::transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy
        )
    {
    int32_t ct = mMemberIds.size();

    PyObject* tr = PyList_New(ct);
    if (tr == nullptr) {
        return nullptr;
        }

    for (int32_t ix = 0; ix < ct; ++ix) {
        PyObject* item = c.convert(mMemberIds[ix]);
        if (item == nullptr) {
            Py_DECREF(tr);
            return nullptr;
            }
        
        PyList_SET_ITEM(tr, ix, item);
        }

    return tr;
    }
