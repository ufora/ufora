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

#include "../core/threading/Queue.hpp"
#include "../core/lassert.hpp"
#include "../core/cppml/CPPMLEquality.hppml"
#include "../core/threading/CallbackScheduler.hppml"

#include "../core/Logging.hpp"



template<class T>
void assertQueueContainsAndRemove(Queue<T>& queue, T in, PolymorphicSharedPtr<CallbackScheduler> scheduler)
	{
	scheduler->blockUntilPendingHaveExecuted();

	Nullable<T> elt = queue.getNonblock();
	
	lassert_dump(
		elt && cppmlCmp(*elt, in) == 0,
		"In " << __PRETTY_FUNCTION__ << "\nExpected\n\t" << prettyPrintString(in) 
			<< "\nbut got\n\t" << prettyPrintString(elt) << "\n"
		);
	}

template<class T>
void assertQueueContainsPredicateAndRemove(Queue<T>& queue, boost::function<bool (T)> predicate, PolymorphicSharedPtr<CallbackScheduler> scheduler)
	{
	scheduler->blockUntilPendingHaveExecuted();

	Nullable<T> elt = queue.getNonblock();
	
	lassert_dump(
		elt && predicate(*elt),
		"In " << __PRETTY_FUNCTION__ << ", got\n\t" << prettyPrintString(elt) << "\n"
		);
	}

template<class T>
void assertQueueContainsAndRemoveRegardlessOfOrder(Queue<T>& queue, T in, PolymorphicSharedPtr<CallbackScheduler> scheduler)
	{
	scheduler->blockUntilPendingHaveExecuted();

	std::vector<T> other;

	bool found = false;

	while (queue.size())
		other.push_back(*queue.getNonblock());

	for (long k = 0; k < other.size();k++)
		if (other[k] == in)
			found = true;
		else
			queue.write(other[k]);

	if (!found)
		LOG_ERROR << in << " not in " << other;

	lassert_dump(found,
		"In " << __PRETTY_FUNCTION__ << "\n"
			<< "Couldn't find " << prettyPrintString(in) 
			<< " within " << prettyPrintString(other)
		);
	}

template<class T>
void assertQueueContains(Queue<T>& queue, T in, PolymorphicSharedPtr<CallbackScheduler> scheduler)
	{
	scheduler->blockUntilPendingHaveExecuted();

	Nullable<T> elt = queue.getNonblock();
	
	lassert_dump(
		elt && cppmlCmp(*elt, in) == 0,
		"In " << __PRETTY_FUNCTION__ << "\nExpected\n\t" << prettyPrintString(in) 
			<< "\nbut got\n\t" << prettyPrintString(elt) << "\n"
		);

	//push everything back onto the queue
	Queue<T> otherQueue;
	otherQueue.write(*elt);

	while ((elt = queue.getNonblock()))
		otherQueue.write(*elt);

	while ((elt = otherQueue.getNonblock()))
		queue.write(*elt);
	}

template<class T>
bool pushEventIntoQueue(boost::weak_ptr<Queue<T> > inQueuePtr, T value)
	{
	boost::shared_ptr<Queue<T> > ptr = inQueuePtr.lock();

	if (!ptr)
		return false;

	ptr->write(value);

	return true;
	}

template<class T>
boost::shared_ptr<Queue<T> > subscribeQueueToBroadcaster(EventBroadcaster<T>& broadcaster)
	{
	boost::shared_ptr<Queue<T> > queue(new Queue<T>());

	broadcaster.subscribe(
		boost::bind(
			&pushEventIntoQueue<T>,
			queue,
			boost::arg<1>()
			)
		);

	return queue;
	}


template<class T>
Nullable<T> getFromQueueTimed(Queue<T>& queue, double timeout = 1.0)
	{
	T tr;

	if (queue.getTimeout(tr, timeout))
		return null() << tr;

	return null();
	}


