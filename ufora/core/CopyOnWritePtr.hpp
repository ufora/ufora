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

#include <boost/shared_ptr.hpp>

template <class T>
class CopyOnWritePtr {
public:
	CopyOnWritePtr() :
			mPtr()
		{
		}

	CopyOnWritePtr(T* t) :
			mPtr(t)
		{
		}

	CopyOnWritePtr(const boost::shared_ptr<T>& ptr) :
			mPtr(ptr)
		{
		}

	CopyOnWritePtr(const CopyOnWritePtr& ptr) :
			mPtr(ptr.mPtr)
		{
		}

	CopyOnWritePtr& operator=(const CopyOnWritePtr& rhs)
		{
		mPtr = rhs.mPtr;
		return *this;
		}

	const T& operator*() const
		{
		return *mPtr;
		}

	const T* operator->() const
		{
		return mPtr.operator->();
		}

	T& operator*()
		{
		copyIfNecessary();
		return *mPtr;
		}

	T* operator->()
		{
		copyIfNecessary();
		return mPtr.operator->();
		}

	void reset()
		{
		mPtr.reset();
		}

private:
	void copyIfNecessary()
		{
		if (mPtr && !mPtr.unique())
			{
			boost::shared_ptr<T> ptr = mPtr;

			mPtr = boost::shared_ptr<T>(new T(*ptr));
			}
		}

	boost::shared_ptr<T> mPtr;
};

