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
#pragma

#include <boost/thread.hpp>
#include <boost/bind.hpp>
#include "../containers/TwoWaySetMap.hpp"
#include "../containers/MapWithIndex.hpp"
#include "../Logging.hpp"
#include "../Clock.hpp"

namespace Ufora {

/***********
ThreadPoolWithDependencies

A threadpool whose tasks may have dependencies on each other. Each task consists of an id, a
definition, and a set of dependencies (represented as task ids). Tasks do not execute until all
their dependent tasks have executed.

This object remembers all task ids it executes, so that it's legal to define a task that
depends on a task that has already completed.

It is also legal to depend on a task that has not been defined yet. In this case, the task
will block forever if the subtask is never defined.

************/

template<
	typename task_identifier_type = std::string,
	typename task_definition_type = boost::function0<void>,
	typename priority_type = long
	>
class ThreadPoolWithDependencies {
public:
	ThreadPoolWithDependencies(long inInitialThreadcount) :
			mIsStillValid(true)
		{
		for (long k = 0; k < inInitialThreadcount; k++)
			mThreads.push_back(
				boost::shared_ptr<boost::thread>(
					new boost::thread(
						boost::bind(
							&ThreadPoolWithDependencies::threadLoop,
							this
							)
						)
					)
				);
		}

	//our destructor blocks until currently pending tasks have exited. Long-running tasks
	//could cause this function to take a long time.
	~ThreadPoolWithDependencies()
		{
			{
			boost::mutex::scoped_lock lock(mMutex);

			mIsStillValid = false;

			mComputableTasksExist.notify_all();
			}

		for (auto threadPtr: mThreads)
			threadPtr->join();
		}

	template<class task_identifier_set_type>
	void addTask(
			task_identifier_type id,
			task_definition_type definition,
			priority_type priority,
			//expects container<task_id_type>
			const task_identifier_set_type& taskDependencies,
			bool dropIfTaskAlreadyDefined
			)
		{
		boost::mutex::scoped_lock lock(mMutex);

		LOG_DEBUG << "Scheduling " << id << "\n\tdeps=" << taskDependencies;

		if (dropIfTaskAlreadyDefined && hasEverSeenTask_(id))
			return;

		lassert(!hasEverSeenTask_(id));

		std::set<task_identifier_type> actualTaskDeps;

		for (auto taskId: taskDependencies)
			{
			if (mCompletedTasks.find(taskId) == mCompletedTasks.end())
				actualTaskDeps.insert(taskId);
			}

		mTaskDefinitions[id] = definition;
		mTaskPriorities[id] = priority;

		if (actualTaskDeps.size())
			mDependencyGraph.insert(id, actualTaskDeps);
		else
			{
			mComputableTasks.set(id, priority);

			mComputableTasksExist.notify_one();
			}
		}

	bool hasTaskExecuted(task_identifier_type taskId) const
		{
		boost::mutex::scoped_lock lock(mMutex);

		return mCompletedTasks.find(taskId) != mCompletedTasks.end();
		}

	bool anyExecutingOrPending() const
		{
		boost::mutex::scoped_lock lock(mMutex);

		return mComputableTasks.size() || mCurrentlyExecutingTasks.size();
		}

	void blockUntilTaskIsComplete(task_identifier_type task)
		{
		boost::mutex::scoped_lock lock(mMutex);

		while (mCompletedTasks.find(task) == mCompletedTasks.end())
			mTaskWasCompleted.wait(lock);
		}

private:
	bool hasEverSeenTask_(task_identifier_type id)
		{
		return mTaskDefinitions.find(id) != mTaskDefinitions.end() ||
				mCompletedTasks.find(id) != mCompletedTasks.end();
		}

	void threadLoop()
		{
		try {
			boost::mutex::scoped_lock lock(mMutex);

			if (!mIsStillValid)
				return;

			while (true)
				{
				while (!mComputableTasks.size())
					{
					mComputableTasksExist.wait(lock);

					if (!mIsStillValid)
						return;
					}

				priority_type pri = mComputableTasks.highestValue();

				task_identifier_type task = *mComputableTasks.getKeys(pri).begin();

				mCurrentlyExecutingTasks.insert(task);

				mComputableTasks.drop(task);

				task_definition_type taskDefinition = mTaskDefinitions[task];

				mTaskPriorities.erase(task);

				mTaskDefinitions.erase(task);

				LOG_DEBUG << "Executing " << task;

				double t0 = curClock();

				lock.unlock();

				try {
					taskDefinition();
					}
				catch(std::logic_error& e)
					{
					LOG_CRITICAL << "task " << task << " threw an exception:\n" << e.what();
					}
				catch(...)
					{
					LOG_CRITICAL << "task " << task << " threw an exception.";
					}

				lock.lock();

				LOG_DEBUG << "Completed in " << curClock() - t0 << ": " << task;

				if (!mIsStillValid)
					return;

				mCompletedTasks.insert(task);

				mCurrentlyExecutingTasks.erase(task);

				std::set<task_identifier_type> tasksDependingOnUs = mDependencyGraph.getKeys(task);

				mDependencyGraph.dropValue(task);

				for (auto task: tasksDependingOnUs)
					if (mDependencyGraph.getValues(task).size() == 0)
						{
						mComputableTasks.set(task, mTaskPriorities[task]);
						mComputableTasksExist.notify_one();
						}

				mTaskWasCompleted.notify_all();
				}
			}
		catch(...)
			{
			LOG_CRITICAL << "threadloop exited unexpectedly.";
			}
		}

	mutable boost::mutex mMutex;

	bool mIsStillValid;

	std::vector<boost::shared_ptr<boost::thread> > mThreads;

	//tasks that are executing. definitions are no longer populated
	std::set<task_identifier_type> mCurrentlyExecutingTasks;

	//definitions of tasks that are defined but not yet checked out for computation
	std::map<task_identifier_type, task_definition_type> mTaskDefinitions;

	//tasks that are computable but not checked out
	MapWithIndex<task_identifier_type, priority_type> mComputableTasks;

	//tasks that have been completed at some point in the past
	std::set<task_identifier_type> mCompletedTasks;

	//dependencies of uncompleted tasks on other uncompleted tasks
	TwoWaySetMap<task_identifier_type, task_identifier_type> mDependencyGraph;

	//priority of tasks. unpopulated once a task is checked out
	std::map<task_identifier_type, priority_type> mTaskPriorities;

	boost::condition_variable mComputableTasksExist;

	boost::condition_variable mTaskWasCompleted;
};

}
