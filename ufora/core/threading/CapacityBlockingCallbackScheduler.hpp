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
#include "CallbackScheduler.hppml"

class CapacityBlockingCallbackScheduler {
public:
	CapacityBlockingCallbackScheduler(PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler, uint64_t inMaxCapacity);

	void scheduleButBlockIfCapacityIsExceeded(boost::function0<void> inFunc, uint64_t inSize);

	void setMaxCapacity(uint64_t inNewCapacity);

	uint64_t getMaxCapacity(void) const;

	bool blockUntilPendingHaveExecuted();

	bool blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();

	bool blockUntilPendingHaveExecutedAndQueueIsEmpty(bool logDelays=true);
private:
	void callAndDecrementCapacity(boost::function0<void> inFunc, uint64_t capacity);

	void decrementCapacity(uint64_t capacity);

	PolymorphicSharedPtr<CallbackScheduler> mCallbackScheduler;

	uint64_t mCurSizeScheduled;

	uint64_t mMaxCapacity;

	boost::condition_variable mCurCapacityChanged;

	boost::mutex mMutex;
};

