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

#include <vector>
#include <map>
#include <set>
#include "../lassert.hpp"

template<class T>
class VectorWithIndex {
public:
	VectorWithIndex()
		{
		}

	void push_back(const T& in)
		{
		mElements.push_back(in);
		mIndices[in].insert(mElements.size()-1);
		}

	void pop_back()
		{
		lassert(size());
		removeAndSwapLastFor(size()-1);
		}

	typename std::vector<T>::const_iterator begin() const
		{
		return mElements.begin();
		}

	typename std::vector<T>::const_iterator end() const
		{
		return mElements.end();
		}

	const T& operator[](long ix) const
		{
		lassert(ix >= 0 && ix < mElements.size());
		return mElements[ix];
		}

	size_t size() const
		{
		return mElements.size();
		}

	bool contains(const T& in) const
		{
		return mIndices.find(in) != mIndices.end();
		}

	const std::set<size_t>& indicesContaining(const T& in) const
		{
		static std::set<size_t> empty;

		auto it = mIndices.find(in);

		if (it == mIndices.end())
			return empty;

		return it->second;
		}

	bool isHighestIndexFor(const T& in, long index) const
		{
		auto it = mIndices.find(in);

		if (it == mIndices.end())
			return false;

		lassert(it->second.size());

		return *it->second.rbegin() == index;
		}

	const std::map<T, std::set<size_t> >& getIndices() const
		{
		return mIndices;
		}

	void clear()
		{
		mElements.clear();
		mIndices.clear();
		}

	//remove the lowest-indexed copy of 'in' and swap the last value in the
	//vector into its position. This prevents us from having to reindex the entire
	//vector.
	void removeAndSwapLastFor(const T& in)
		{
		const auto& indices = indicesContaining(in);

		lassert(indices.size());

		removeAndSwapLastForIndex(*indices.begin());
		}

	void removeAndSwapLastForIndex(long index)
		{
		lassert(index >= 0 && index < size());

		mIndices[mElements[index]].erase(index);

		if (mIndices[mElements[index]].size() == 0)
			mIndices.erase(mElements[index]);

		long lastIndex = mElements.size() - 1;

		if (lastIndex != index)
			{
			mIndices[mElements[lastIndex]].erase(lastIndex);
			mIndices[mElements[lastIndex]].insert(index);

			mElements[index] = mElements[lastIndex];
			}

		mElements.pop_back();
		}

private:
	std::vector<T> mElements;

	std::map<T, std::set<size_t> > mIndices;
};
