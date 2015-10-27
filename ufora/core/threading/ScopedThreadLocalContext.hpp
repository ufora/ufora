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

#include <boost/thread.hpp>
#include "../lassert.hpp"

namespace Ufora {
namespace threading {

/****
ScopedThreadLocalContext

Creates a thread-local stack for objects of a particular type.

Usage:
T aValue(...);

	{
	ScopedThreadLocalContext<T> contextSetter(aValue);

	//within subscopes: 
	lassert(ScopedThreadLocalContext<T>::has());
	lassert(&ScopedThreadLocalContext<T>::get() == &aValue);
	lassert(ScopedThreadLocalContext<T>::getPtr() == &aValue);

	}

****/

template <class T>
class ScopedThreadLocalContext  {
public:
		//reset the context to 'null'
		ScopedThreadLocalContext() : mOriginalValue(mContext)
			{
			mContext = 0;
			}

		//set the context in all subscopes to 'in'
		ScopedThreadLocalContext(T& in) : mOriginalValue(mContext)
			{
			mContext = &in;
			}

		//set the context in all subscopes to 'in'
		ScopedThreadLocalContext(T* in) : mOriginalValue(mContext)
			{
			mContext = in;
			}

		~ScopedThreadLocalContext()
			{
			mContext = mOriginalValue;
			}

		static bool has(void)
			{
			return mContext;
			}

		static T& get(void)
			{
			lassert(mContext);
			return *mContext;
			}

		static T* getPtr(void)
			{
			return mContext;
			}

		T* getOriginalPtr() const
			{
			return mOriginalValue;
			}
private:
		static __thread T* mContext;
		T* mOriginalValue;
};

template<class T>
__thread T* ScopedThreadLocalContext<T>::mContext = 0;

}
}


