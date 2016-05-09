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
#include "ScopedPyThreads.hpp"

ScopedPyThreads::ScopedPyThreads()
	{
	if (!getPtr()->get())
		{
		mState = PyEval_SaveThread();
		getPtr()->reset(new PyThreadState*(mState));
		}
		else
		{
		mState = 0;
		}
	}
ScopedPyThreads::~ScopedPyThreads()
	{
	if (mState)
		{
		getPtr()->reset(0);
		PyEval_RestoreThread(mState);
		}
	}
boost::thread_specific_ptr<PyThreadState*>* ScopedPyThreads::getPtr(void)
	{
	static boost::thread_specific_ptr<PyThreadState*>* p = 0;

	if (!p)
		p = new boost::thread_specific_ptr<PyThreadState*>();

	return p;
	}

ScopedPyThreadsReacquire::ScopedPyThreadsReacquire() :
			mAcquired(false)
	{
	PyThreadState** threadState = ScopedPyThreads::getPtr()->get();

	if (threadState)
		{
		PyEval_RestoreThread(*threadState);
		ScopedPyThreads::getPtr()->reset(0);
		mAcquired = true;
		}
	}
ScopedPyThreadsReacquire::~ScopedPyThreadsReacquire()
	{
	if (mAcquired)
		ScopedPyThreads::getPtr()->reset(new PyThreadState*(PyEval_SaveThread()));
	}


