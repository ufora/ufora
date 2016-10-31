///***************************************************************************
//   Copyright 2015-2016 Ufora Inc.
//
//   Licensed under the Apache License, Version 2.0 (the "License");
//   you may not use this file except in compliance with the License.
//   You may obtain a copy of the License at
//
//       http://www.apache.org/licenses/LICENSE-2.0
//
//   Unless required by applicable law or agreed to in writing, software
//   distributed under the License is distributed on an "AS IS" BASIS,
//   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//   See the License for the specific language governing permissions and
//   limitations under the License.
//****************************************************************************/

#include "CompilerCache.hpp"


template<class T1, class T2>
void GenericCompilerCache<T1, T2>::set(const CompilerMapKey& inKey, const CompilerMapValue& inObj)
	{
	boost::recursive_mutex::scoped_lock lock(mMutex);

	if (auto res = get(inKey))
		{
		return;
		}
	mPrimaryMap.set(inKey, inObj);
	mSecondaryMap.set(inKey, inObj);
	}

template<class T1, class T2>
Nullable<ControlFlowGraph> GenericCompilerCache<T1, T2>::get(const CompilerMapKey& inKey) const
	{
	boost::recursive_mutex::scoped_lock lock(mMutex);
	Nullable<ControlFlowGraph> result = mPrimaryMap.get(inKey);
	if (result)
		return result;

	result = mSecondaryMap.get(inKey);
	if (result)
		mPrimaryMap.set(inKey, *result);

	return result;
	}

template
void GenericCompilerCache<CompilerCachePrimaryMap, InMemoryCompilerStore>::set(
		const CompilerMapKey& inKey,
		const CompilerMapValue& inObj
		);

template
Nullable<ControlFlowGraph> GenericCompilerCache<CompilerCachePrimaryMap, InMemoryCompilerStore>::get(const CompilerMapKey& inKey) const;

template
void GenericCompilerCache<CompilerCachePrimaryMap, DummyCompilerStore>::set(
		const CompilerMapKey& inKey,
		const CompilerMapValue& inObj
		);

template
Nullable<ControlFlowGraph> GenericCompilerCache<CompilerCachePrimaryMap, DummyCompilerStore>::get(const CompilerMapKey& inKey) const;

template
void GenericCompilerCache<InMemoryCompilerStore, DummyCompilerStore>::set(
		const CompilerMapKey& inKey,
		const CompilerMapValue& inObj
		);

template
Nullable<ControlFlowGraph> GenericCompilerCache<InMemoryCompilerStore, DummyCompilerStore>::get(const CompilerMapKey& inKey) const;

template
void GenericCompilerCache<DummyCompilerStore, OnDiskCompilerStore>::set(
		const CompilerMapKey& inKey,
		const CompilerMapValue& inObj
		);

template
Nullable<ControlFlowGraph> GenericCompilerCache<DummyCompilerStore, OnDiskCompilerStore>::get(const CompilerMapKey& inKey) const;


