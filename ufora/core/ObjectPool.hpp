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

#include "threading/Queue.hpp"
#include <boost/bind.hpp>

namespace Ufora {

/*************

ObjectPool

Manages a pool of objects. Objects can be checked out and held using a "handle". When all copies
of the handle are destroyed, the object is placed back into the object queue to be reused. Objects
are never recycled, so the number of objects allocated will be as large as the number of distinct
users.

Handles may outlive the ObjectPool and still be valid.

**************/

template<class T>
class ObjectPool {
public:
	class CallOnDestroy {
	public:
		CallOnDestroy(boost::function0<void> in) : m(in)
			{
			}

		~CallOnDestroy()
			{
			m();
			}

	private:
		boost::function0<void> m;
	};

	class Handle {
	public:
		Handle()
			{
			}

		Handle(boost::shared_ptr<CallOnDestroy> destroy, boost::shared_ptr<T> object) : 
				mObjectPtr(object),
				mDestroyer(destroy)
			{
			}

		T& operator*() const
			{
			return *mObjectPtr;
			}

		T* operator->() const
			{
			return &*mObjectPtr;
			}

		operator bool() const
			{
			return (bool)mObjectPtr;
			}

	private:
		boost::shared_ptr<CallOnDestroy> mDestroyer;

		boost::shared_ptr<T> mObjectPtr;
	};

	ObjectPool(boost::function0<boost::shared_ptr<T> > inConstructor) : 
			mConstructor(inConstructor),
			mObjects(new Queue<boost::shared_ptr<T> >())
		{
		}

	Handle get()
		{
		Nullable<boost::shared_ptr<T> > ptr = mObjects->getNonblock();

		if (!ptr)
			ptr = mConstructor();

		return Handle(
			boost::shared_ptr<CallOnDestroy>(
				new CallOnDestroy(
					boost::bind(
						&ObjectPool::checkin,
						mObjects,
						*ptr
						)
					)
				),
			*ptr
			);
		}

private:
	static void checkin(
					boost::shared_ptr<Queue<boost::shared_ptr<T> > > queue,
					boost::shared_ptr<T> object
					)
		{
		queue->write(object);
		}


	boost::function0<boost::shared_ptr<T> > mConstructor;

	boost::shared_ptr<Queue<boost::shared_ptr<T> > > mObjects;
};

}
