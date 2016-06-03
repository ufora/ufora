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
#include <boost/enable_shared_from_this.hpp>
#include <vector>
#include <boost/bind.hpp>
#include "threading/ScopedThreadLocalContext.hpp"
#include "math/Nullable.hpp"
#include <boost/type_traits.hpp>

namespace DependencyGraph {

class Dirtyable;

class Changeable;

template<class T>
class ComputedProperty;

class Graph {
public:
	Graph();

	~Graph();

	void markDirty(boost::shared_ptr<Dirtyable> dirty);

	long recompute();

	long recomputeBelow(long dirtynessLevel);

	long valuesComputed() const
		{
		return mValuesComputed;
		}

	double timeElapsed() const
		{
		return mTimeElapsed;
		}

private:
	std::map<long, std::vector<boost::shared_ptr<Dirtyable> > > mDirtyElementsByLevel;

	double mTimeElapsed;

	long mValuesComputed;
};

class Dirtyable : public boost::enable_shared_from_this<Dirtyable> {
public:
	Dirtyable(Graph& inGraph);

	virtual ~Dirtyable() {};

	void markDirty();

	void clean();

	virtual void dependsOnChangableAtLevel(long level) = 0;

	virtual long level() = 0;

	void initializeDirtyable();

	virtual void teardown() {};

protected:
	virtual void makeClean() = 0;

private:
	Graph* mGraph;

	bool mDirty;

	bool mIsInitialized;
};

class Changeable {
protected:
	virtual ~Changeable() {};

	void registerDependency(long fromLevel);

	void addListener(boost::shared_ptr<Dirtyable> inListener);

	void onChanged();

private:
	std::vector<boost::weak_ptr<Dirtyable> > mListeners;
};

template<class T>
class Mutable : public Changeable {
public:
	Mutable() : mValue()
		{
		}

	const T& get()
		{
		registerDependency(0);

		return mValue;
		}

	void set(const T& in, bool forceDirty = false)
		{
		if (mValue != in || forceDirty)
			{
			mValue = in;
			onChanged();
			}
		}

	void markDirty()
		{
		onChanged();
		}

private:
	T mValue;
};

template<class T>
class ComputedProperty : public Dirtyable, public Changeable {
public:
	ComputedProperty(Graph& inGraph) :
			Dirtyable(inGraph),
			mLevel(0),
			mMinLevel(0),
			mValue()
		{
		}

	~ComputedProperty()
		{
		for (auto it = mOnDestroy.begin(); it != mOnDestroy.end(); ++it)
			(*it)();
		}

	void addOnDestroy(boost::function0<void> in)
		{
		mOnDestroy.push_back(in);
		}

	virtual void teardown()
		{
		mOnDestroy.clear();
		}

	virtual void dependsOnChangableAtLevel(long level)
		{
		mLevel = std::max(level + 1, mLevel);
		}

	void makeClean()
		{
		Ufora::threading::ScopedThreadLocalContext<Dirtyable> contextSetter(*this);

		mLevel = mMinLevel;

		T value = compute();

		if (value != mValue)
			{
			mValue = value;
			onChanged();
			}
		}

	const T& get()
		{
		initializeDirtyable();

		registerDependency(mLevel);

		return mValue;
		}

	virtual long level()
		{
		return mLevel;
		}

	void setMinLevel(long inLevel)
		{
		mMinLevel = inLevel;

		if (mLevel < inLevel)
			mLevel = inLevel;
		}

protected:
	virtual T compute() const = 0;

	T mValue;

private:
	long mLevel;

	long mMinLevel;

	std::vector<boost::function0<void> > mOnDestroy;
};

template<class result_type, class callable_type>
class ComputedPropertyFromCallable : public ComputedProperty<result_type> {
public:
	ComputedPropertyFromCallable(Graph& inGraph, callable_type inCallable) :
			ComputedProperty<result_type>(inGraph),
			mCallable(inCallable)
		{
		}

protected:
	virtual result_type compute() const
		{
		return mCallable();
		}

private:
	callable_type mCallable;
};

template<class result_type, class callable_type>
class ComputedPropertyFromCallableWithPrior : public ComputedProperty<result_type> {
public:
	ComputedPropertyFromCallableWithPrior(Graph& inGraph, callable_type inCallable) :
			ComputedProperty<result_type>(inGraph),
			mCallable(inCallable)
		{
		}

protected:
	virtual result_type compute() const
		{
		return mCallable(this->mValue);
		}

private:
	callable_type mCallable;
};

template<class T>
class ExtractCallableType {
public:
	typedef typename boost::remove_reference<T>::type unrefed_type;

	typedef typename boost::remove_const<unrefed_type>::type result_type;
};

template<class callable_type>
auto bind(Graph& inGraph, const callable_type& inCallable) ->
		boost::shared_ptr<ComputedProperty<
			typename ExtractCallableType<decltype(inCallable())>::result_type
			> >
	{
	typedef typename ExtractCallableType<decltype(inCallable())>::result_type result_type;

	return boost::shared_ptr<ComputedProperty<result_type> >(
		new ComputedPropertyFromCallable<result_type, callable_type>(inGraph, inCallable)
		);
	}

template<class callable_type>
auto bindWithPrior(Graph& inGraph, const callable_type& inCallable) ->
		boost::shared_ptr<ComputedProperty<
			typename ExtractCallableType<decltype(inCallable())>::result_type
			> >
	{
	typedef typename ExtractCallableType<decltype(inCallable())>::result_type result_type;

	return boost::shared_ptr<ComputedProperty<result_type> >(
		new ComputedPropertyFromCallableWithPrior<result_type, callable_type>(inGraph, inCallable)
		);
	}

template<class key_type, class result_type>
class Index {
public:
	Index(Graph& inGraph) :
			mGraph(inGraph)
		{
		}

	void add(const key_type& key, boost::shared_ptr<ComputedProperty<result_type> > property)
		{
		boost::shared_ptr<Nullable<result_type> > lastValue(new Nullable<result_type>);

		boost::shared_ptr<ComputedProperty<int> > updater =
			::DependencyGraph::bind(mGraph, boost::bind(
				&Index::updateKeyProperty,
				this,
				lastValue,
				key,
				property.get()
				)
			);

		mKeyUpdaters[property.get()] = updater;
		property->addOnDestroy(
			boost::bind(
				&Index::dropKeyProperty,
				this,
				lastValue,
				key,
				property.get()
				)
			);

		updater->get();
		}

	const std::map<key_type, long>& get(const result_type& in)
		{
		ensureKeyset(in);
		return *mKeysetMutablesByResult[in]->get();
		}

	void ensureKeyset(const result_type& in)
		{
		auto it = mKeysetMutablesByResult.find(in);

		if (it == mKeysetMutablesByResult.end())
			{
			mKeysetMutablesByResult[in].reset(
				new Mutable<boost::shared_ptr<std::map<key_type, long> > >()
				);

			mKeysetsByResult[in].reset(new std::map<key_type, long>());

			mKeysetMutablesByResult[in]->set(mKeysetsByResult[in]);
			}
		}

	const std::map<result_type, boost::shared_ptr<std::map<key_type, long> > >& getResultMap() const
		{
		return mKeysetsByResult;
		}

private:
	void update(result_type r, key_type k, long byAmount)
		{
		ensureKeyset(r);

		mKeysetMutablesByResult[r]->markDirty();

		auto& keysetMap = *mKeysetsByResult[r];

		keysetMap[k] += byAmount;

		if (keysetMap[k] == 0)
			keysetMap.erase(k);

		if (keysetMap.size() == 0)
			{
			//this is a legal thing to do because we have just called 'markDirty' on the mutable.
			//anybody listening will have to resubscribe if they need it. we will still end up
			//leaving behind a bunch of
			mKeysetsByResult.erase(r);
			mKeysetMutablesByResult.erase(r);
			}
		}

	int updateKeyProperty(
				boost::shared_ptr<Nullable<result_type> > lastValue,
				key_type key,
				ComputedProperty<result_type>* property
				)
		{
		result_type newResult = property->get();

		if (*lastValue && **lastValue == newResult)
			return 0;

		if (*lastValue)
			update(**lastValue, key, -1);

		update(newResult, key, 1);

		*lastValue = newResult;

		return 0;
		}

	void dropKeyProperty(
				boost::shared_ptr<Nullable<result_type> > lastValue,
				key_type key,
				ComputedProperty<result_type>* property
				)
		{
		if (*lastValue)
			update(**lastValue, key, -1);

		mKeyUpdaters.erase(property);
		}

	Graph& mGraph;

	std::map<result_type, boost::shared_ptr<std::map<key_type, long> > >
		mKeysetsByResult;

	std::map<result_type, boost::shared_ptr<Mutable<boost::shared_ptr<std::map<key_type, long> > > > >
		mKeysetMutablesByResult;

	std::map<ComputedProperty<result_type>*, boost::shared_ptr<ComputedProperty<int> > >
		mKeyUpdaters;
};




}

