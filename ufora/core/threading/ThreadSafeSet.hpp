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

#include "../math/Nullable.hpp"
#include <boost/thread.hpp>

//a thread-safe set

template<class T>
class ThreadSafeSet {
public:
    //returns true if the map contains key 'in'
    bool contains(const T& in) const
        {
        boost::recursive_mutex::scoped_lock lock(mMutex);
        return mSet.find(in) != mSet.end();
        }

    void insert(const T& in)
        {
        boost::recursive_mutex::scoped_lock lock(mMutex);
        mSet.insert(in);
        }

    void erase(const T& in)
        {
        boost::recursive_mutex::scoped_lock lock(mMutex);
        mSet.erase(in);
        }

    //remove the first element from the set and return if present, or return null() if set is
    //empty
    Nullable<T> popFirst()
        {
        Nullable<T> tr;

            {
            boost::recursive_mutex::scoped_lock lock(mMutex);
            if (mSet.size())
                {
                tr = *mSet.begin();
                mSet.erase(mSet.begin());
                }
            }

        return tr;
        }

    size_t size() const
        {
        boost::recursive_mutex::scoped_lock lock(mMutex);
        return mSet.size();
        }

    std::set<T> getSet() const
        {
        boost::recursive_mutex::scoped_lock lock(mMutex);
        return mSet;
        }

private:
    std::set<T> mSet;
    mutable boost::recursive_mutex mMutex;
};
