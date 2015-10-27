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
#include "DependencyGraph.hpp"
#include "Clock.hpp"

namespace DependencyGraph {

Graph::Graph() :
		mTimeElapsed(0),
		mValuesComputed(0)
	{
	}

Graph::~Graph()
	{
	for (auto it = mDirtyElementsByLevel.begin(); it != mDirtyElementsByLevel.end(); ++it)
		for (auto it2 = it->second.begin(); it2 != it->second.end(); it2++)
			(*it2)->teardown();
	}

void Graph::markDirty(boost::shared_ptr<Dirtyable> dirty)
	{
	mDirtyElementsByLevel[dirty->level()].push_back(dirty);
	}

long Graph::recompute()
	{
	double t0 = curClock();

	long count = 0;

	while (mDirtyElementsByLevel.size())
		{
		auto& eltVec = mDirtyElementsByLevel.begin()->second;

		if (eltVec.size())
			{
			boost::weak_ptr<Dirtyable> weakDirtyPtr = eltVec.back();

			eltVec.pop_back();

			boost::shared_ptr<Dirtyable> dirtyPtr = weakDirtyPtr.lock();

			if (dirtyPtr)
				dirtyPtr->clean();
			
			count++;
			}
		else
			mDirtyElementsByLevel.erase(mDirtyElementsByLevel.begin());
		}

	mValuesComputed += count;
	mTimeElapsed += curClock() - t0;
	
	return count;
	}

long Graph::recomputeBelow(long dirtynessLevel)
	{
	double t0 = curClock();

	long count = 0;

	while (mDirtyElementsByLevel.size() && mDirtyElementsByLevel.begin()->first < dirtynessLevel)
		{
		auto& eltVec = mDirtyElementsByLevel.begin()->second;

		if (eltVec.size())
			{
			boost::weak_ptr<Dirtyable> weakDirtyPtr = eltVec.back();

			eltVec.pop_back();

			boost::shared_ptr<Dirtyable> dirtyPtr = weakDirtyPtr.lock();

			if (dirtyPtr)
				dirtyPtr->clean();
			
			count++;
			}
		else
			mDirtyElementsByLevel.erase(mDirtyElementsByLevel.begin());
		}

	mValuesComputed += count;
	mTimeElapsed += curClock() - t0;
	
	return count;
	}


Dirtyable::Dirtyable(Graph& inGraph) : 
		mGraph(&inGraph),
		mDirty(false),
		mIsInitialized(false)
	{
	}

void Dirtyable::initializeDirtyable()
	{
	if (mIsInitialized)
		return;

	mIsInitialized = true;
	markDirty();
	}
	

void Dirtyable::markDirty()
	{
	if (!mDirty)
		{
		mDirty = true;
		mGraph->markDirty(shared_from_this());
		}
	}

void Dirtyable::clean()
	{
	if (mDirty)
		{
		makeClean();
		mDirty = false;
		}
	}

void Changeable::registerDependency(long level)
	{
	Dirtyable* dirtyable = Ufora::threading::ScopedThreadLocalContext<Dirtyable>::getPtr();
	if (dirtyable)
		{
		addListener(dirtyable->shared_from_this());
		dirtyable->dependsOnChangableAtLevel(level);
		}
	}

void Changeable::addListener(boost::shared_ptr<Dirtyable> inListener)
	{
	mListeners.push_back(inListener);
	}

void Changeable::onChanged()
	{
	for (auto it = mListeners.begin(); it != mListeners.end(); ++it)
		{
		boost::shared_ptr<Dirtyable> p = it->lock();
		if (p)
			p->markDirty();
		}

	mListeners.clear();
	}

















}
