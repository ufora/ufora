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

#include <cstddef>


class PyObjectPtr {
public:
    PyObjectPtr() noexcept
        : mPtr(nullptr)
        {
        }

    PyObjectPtr(const PyObjectPtr& p) noexcept
        : mPtr(p.mPtr)
        {
        Py_XINCREF(mPtr);
        }

    PyObjectPtr(PyObjectPtr&& other) noexcept
        : mPtr(other.mPtr)
        {
        other.mPtr = nullptr;
        }

    static PyObjectPtr unincremented(PyObject* pyObject)
        {
        return PyObjectPtr(pyObject);
        }

    static PyObjectPtr incremented(PyObject* pyObject)
        {
        PyObjectPtr tr(pyObject);
        Py_XINCREF(pyObject);
        return tr;
        }

    ~PyObjectPtr()
        {
        Py_XDECREF(mPtr);
        }

    PyObject* get() const
        {
        return mPtr;
        }

    PyObject* operator->() { 
        return get();
        }

    PyObjectPtr& operator=(const PyObjectPtr& p) noexcept
        {
        PyObject* const old = mPtr;
        mPtr = p.mPtr;
        Py_XINCREF(mPtr);
        Py_XDECREF(old);
        return *this;
        }

    PyObjectPtr& operator=(PyObjectPtr&& other) noexcept
        {
        if (mPtr != other.mPtr) {
            Py_XDECREF(mPtr);
            mPtr = other.mPtr;
            other.mPtr = nullptr;
            }
        return *this;
        }

    operator bool() const {
        return mPtr != nullptr;
        }

private:
    explicit PyObjectPtr(PyObject* pyObject) noexcept
        : mPtr(pyObject)
        {
        }

    PyObject* mPtr;
    };


/*
compare two PyObjectPtrs:
 */

inline bool operator==(const PyObjectPtr& p1, const PyObjectPtr& p2)
    {
    return p1.get() == p2.get();
    }


inline bool operator!=(const PyObjectPtr& p1, const PyObjectPtr& p2)
    {
    return p1.get() != p2.get();
    }


inline bool operator<(const PyObjectPtr& p1, const PyObjectPtr& p2)
    {
    return p1.get() < p2.get();
    }


inline bool operator>(const PyObjectPtr& p1, const PyObjectPtr& p2)
    {
    return p1.get() > p2.get();
    }


inline bool operator<=(const PyObjectPtr& p1, const PyObjectPtr& p2)
    {
    return p1.get() <= p2.get();
    }


inline bool operator>=(const PyObjectPtr& p1, const PyObjectPtr& p2)
    {
    return p1.get() >= p2.get();
    }


/*
  Compare to nullptr
 */
inline bool operator==(const PyObjectPtr& p1, std::nullptr_t)
    {
    return p1.get() == nullptr;
    }


inline bool operator!=(const PyObjectPtr& p1, std::nullptr_t)
    {
    return p1.get() != nullptr;
    }


inline bool operator<(const PyObjectPtr& p1, std::nullptr_t)
    {
    return p1.get() < nullptr;
    }


inline bool operator>(const PyObjectPtr& p1, std::nullptr_t)
    {
    return p1.get() > nullptr;
    }


inline bool operator<=(const PyObjectPtr& p1, std::nullptr_t)
    {
    return p1.get() <= nullptr;
    }


inline bool operator>=(const PyObjectPtr& p1, std::nullptr_t)
    {
    return p1.get() >= nullptr;
    }


/*
compare PyObjectPtr with PyObject*:
 */

inline bool operator==(const PyObjectPtr& p1, const PyObject* p2)
    {
    return p1.get() == p2;
    }


inline bool operator!=(const PyObjectPtr& p1, const PyObject* p2)
    {
    return p1.get() != p2;
    }


inline bool operator<(const PyObjectPtr& p1, const PyObject* p2)
    {
    return p1.get() < p2;
    }


inline bool operator>(const PyObjectPtr& p1, const PyObject* p2)
    {
    return p1.get() > p2;
    }


inline bool operator<=(const PyObjectPtr& p1, const PyObject* p2)
    {
    return p1.get() <= p2;
    }


inline bool operator>=(const PyObjectPtr& p1, const PyObject* p2)
    {
    return p1.get() >= p2;
    }


/*
compare PyObject* to PyObjectPtrs:
 */

inline bool operator==(const PyObject* p1, const PyObjectPtr& p2)
    {
    return p1 == p2.get();
    }


inline bool operator!=(const PyObject* p1, const PyObjectPtr& p2)
    {
    return p1 != p2.get();
    }


inline bool operator<(const PyObject* p1, const PyObjectPtr& p2)
    {
    return p1 < p2.get();
    }


inline bool operator>(const PyObject* p1, const PyObjectPtr& p2)
    {
    return p1 > p2.get();
    }


inline bool operator<=(const PyObject* p1, const PyObjectPtr& p2)
    {
    return p1 <= p2.get();
    }


inline bool operator>=(const PyObject* p1, const PyObjectPtr& p2)
    {
    return p1 >= p2.get();
    }


