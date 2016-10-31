/***************************************************************************
   Copyright 2015-2016 Ufora Inc.

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

#include "CompilerMapKey.hppml"
#include "CompilerStore.hpp"
#include "OnDiskCompilerStore.hpp"
#include "../../core/threading/ThreadSafeMap.hpp"

class ControlFlowGraph;
class NoncontiguousByteBlock;

typedef ThreadSafeMap<CompilerMapKey, ControlFlowGraph> CompilerCachePrimaryMap;


class CompilerCache {
public:
    virtual void set(const CompilerMapKey& inKey, const CompilerMapValue& inObj) = 0;

    virtual Nullable<ControlFlowGraph> get(const CompilerMapKey& inKey) const = 0;

};

template<class primary_map_type, class secondary_map_type>
class GenericCompilerCache : public CompilerCache {

public:
	GenericCompilerCache(primary_map_type& s1, secondary_map_type& s2)
			: mPrimaryMap(s1), mSecondaryMap(s2) {}

    void set(const CompilerMapKey& inKey, const CompilerMapValue& inObj);

    Nullable<ControlFlowGraph> get(const CompilerMapKey& inKey) const;

private:
	mutable boost::recursive_mutex mMutex;
	primary_map_type& mPrimaryMap;
	secondary_map_type& mSecondaryMap;
};

// This derived class acts as the resource manager of its base class.
class ConcreteCompilerCache : public GenericCompilerCache<CompilerCachePrimaryMap, InMemoryCompilerStore> {
public:
	typedef GenericCompilerCache<ThreadSafeMap<CompilerMapKey, ControlFlowGraph>, InMemoryCompilerStore>  BaseClass;
	ConcreteCompilerCache() : BaseClass(mPrimaryMap, mSecondaryMap) {}

private:
	CompilerCachePrimaryMap mPrimaryMap;
	InMemoryCompilerStore mSecondaryMap;
};


class InMemoryCompilerCache : public GenericCompilerCache<CompilerCachePrimaryMap, DummyCompilerStore> {
public:
	typedef GenericCompilerCache<ThreadSafeMap<CompilerMapKey, ControlFlowGraph>, DummyCompilerStore>  BaseClass;
	InMemoryCompilerCache() : BaseClass(mPrimaryMap, mSecondaryMap) {}

private:
	CompilerCachePrimaryMap mPrimaryMap;
	DummyCompilerStore mSecondaryMap;
};

class SerializingInMemoryCompilerCache : public GenericCompilerCache<InMemoryCompilerStore, DummyCompilerStore> {
public:
	typedef GenericCompilerCache<InMemoryCompilerStore, DummyCompilerStore>  BaseClass;
	SerializingInMemoryCompilerCache() : BaseClass(mPrimaryMap, mSecondaryMap) {}

private:
	InMemoryCompilerStore mPrimaryMap;
	DummyCompilerStore mSecondaryMap;
};

class OnDiskCompilerCache : public GenericCompilerCache<CompilerCachePrimaryMap, OnDiskCompilerStore> {
public:
	typedef GenericCompilerCache<CompilerCachePrimaryMap, OnDiskCompilerStore> BaseClass;
	OnDiskCompilerCache(boost::filesystem::path inBasePath) :
			BaseClass(mPrimaryMap, mSecondaryMap),
			mSecondaryMap(inBasePath.string())
		{}

private:
	CompilerCachePrimaryMap mPrimaryMap;
	OnDiskCompilerStore mSecondaryMap;
};

class OnDiskCompilerCacheTest : public GenericCompilerCache<DummyCompilerStore, OnDiskCompilerStore> {
public:
	typedef GenericCompilerCache<DummyCompilerStore, OnDiskCompilerStore> BaseClass;
	OnDiskCompilerCacheTest(boost::filesystem::path inBasePath) :
			BaseClass(mPrimaryMap, mSecondaryMap),
			mSecondaryMap(inBasePath.string())
		{}

private:
	DummyCompilerStore mPrimaryMap;
	OnDiskCompilerStore mSecondaryMap;
};

