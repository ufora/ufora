/***************************************************************************
   Copyright 2015 Ufora Inc.

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

#include "lassert.hpp"

template <class T>
class HashComparer
{
public:
    bool operator()(const T* lhs, const T* rhs) const
        {
        if (lhs == rhs)
            return false;

        if (lhs == nullptr)
            return true;

        if (rhs ==nullptr)
            return false;

        return lhs->hash() < rhs->hash();
        }
};

template <class T, class comparer = HashComparer<T>>
class OrderedPtr
{
public:
    OrderedPtr() :
        mPtr(nullptr)
        {}

    OrderedPtr(T* ptr) :
        mPtr(ptr)
        {}

    OrderedPtr(const OrderedPtr& other) :
        mPtr(other.mPtr)
        {}

    OrderedPtr& operator=(const OrderedPtr& other)
        {
        if (this != &other)
            mPtr = other.mPtr;
        return *this;
        }

    bool operator<(const OrderedPtr& other) const
        {
        return comparer()(mPtr, other.get());
        }

    bool operator==(const OrderedPtr& other) const
        {
        return mPtr == other.mPtr;
        }

    bool operator!=(const OrderedPtr& other) const
        {
        return mPtr != other.mPtr;
        }

    T* get() const
        {
        return mPtr;
        }

    T& operator*() const
            {
            lassert(mPtr);
            return *get();
            }

    T* operator->() const
            {
            lassert(mPtr);
            return get();
            }

    operator bool() const
            {
            return bool(mPtr);
            }
private:
    T* mPtr;
};

