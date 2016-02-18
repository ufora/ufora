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
#include "../../core/math/Nullable.hpp"
#include "../../core/PolymorphicSharedPtr.hpp"
#include "../../core/threading/ThreadSafeMap.hpp"

class ControlFlowGraph;
class NoncontiguousByteBlock;

/// No-op CompilerStore, used for testing purposes.
class DummyCompilerStore {
public:
	Nullable<ControlFlowGraph> get(const CompilerMapKey& inKey) const;
	void set(const CompilerMapKey& inKey, const ControlFlowGraph& inCFG);
};

class InMemoryCompilerStore {
public:
	typedef PolymorphicSharedPtr<NoncontiguousByteBlock>  SerializedValue;
	typedef ThreadSafeMap<CompilerMapKey, SerializedValue>  CompilerStoreMap;

	InMemoryCompilerStore();
	Nullable<ControlFlowGraph> get(const CompilerMapKey& inKey) const;
	void set(const CompilerMapKey& inKey, const ControlFlowGraph& inCFG);

private:
	CompilerStoreMap mStore;
	uword_t mBytesStored;
	uword_t mLogThreshold;

};

