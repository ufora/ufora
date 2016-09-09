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

#include <set>

template<class T>
class SetWithChanges {
public:
	typedef typename std::set<T>::iterator iterator;
	typedef typename std::set<T>::const_iterator const_iterator;

	size_t size() const
		{
		return mElements.size();
		}

	iterator begin()
		{
		return mElements.begin();
		}

	const iterator begin() const
		{
		return mElements.begin();
		}

	iterator end()
		{
		return mElements.end();
		}

	const iterator end() const
		{
		return mElements.end();
		}

	iterator find(const T& in)
		{
		return mElements.find(in);
		}

	const iterator find(const T& in) const
		{
		return mElements.find(in);
		}

	bool contains(const T& in) const
		{
		return mElements.find(in) != mElements.end();
		}

	void insert(const T& in)
		{
		if (contains(in))
			return;

		mElements.insert(in);

		if (mDropped.find(in) != mDropped.end())
			mDropped.erase(in);
		else
			mAdded.insert(in);
		}

	void erase(const T& in)
		{
		auto it = mElements.find(in);
		if (it == mElements.end())
			return;

		mElements.erase(in);

		if (mAdded.find(in) != mAdded.end())
			mAdded.erase(in);
		else
			mDropped.insert(in);
		}

	void extractChanges(std::set<T>& outAdded, std::set<T>& outDropped)
		{
		outAdded.clear();
		outDropped.clear();
		std::swap(outAdded, mAdded);
		std::swap(outDropped, mDropped);
		}

	void removeFromTrackingSet(const T& in)
		{
		mAdded.erase(in);
		mDropped.erase(in);
		}

private:
	std::set<T> mElements;

	std::set<T> mAdded;

	std::set<T> mDropped;
};