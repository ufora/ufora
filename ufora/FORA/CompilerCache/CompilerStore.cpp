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
#include "CompilerCacheSerializer.hpp"
#include "CompilerStore.hpp"
#include "../ControlFlowGraph/ControlFlowGraph.hppml"
#include "../Core/MemoryPool.hpp"
#include "../VectorDataManager/VectorDataMemoryManager.hppml"
#include "../../core/serialization/IBinaryStream.hpp"
#include "../../core/serialization/INoncontiguousByteBlockProtocol.hpp"
#include "../../core/serialization/OBinaryStream.hpp"
#include "../../core/serialization/ONoncontiguousByteBlockProtocol.hpp"

Nullable<ControlFlowGraph> DummyCompilerStore::get(const CompilerMapKey& inKey) const
	{
	return null();
	}

void DummyCompilerStore::set(const CompilerMapKey& inKey, const ControlFlowGraph& inCFG)
	{
	// no-op
	}


InMemoryCompilerStore::InMemoryCompilerStore() :
	mBytesStored(0),
	mLogThreshold(0)
	{
	}

Nullable<ControlFlowGraph> InMemoryCompilerStore::get(const CompilerMapKey& inKey) const
	{
	auto res = mStore.get(inKey);
	if (!res)
		return null();

	INoncontiguousByteBlockProtocol	protocol(*res);
	IBinaryStream stream(protocol);

	CompilerCacheDuplicatingDeserializer deserializer(
			stream,
			MemoryPool::getFreeStorePool(),
			PolymorphicSharedPtr<VectorDataMemoryManager>()
			);

	ControlFlowGraph tr;
	deserializer.deserialize(tr);
	return null() << tr;
	}

void InMemoryCompilerStore::set(const CompilerMapKey& inKey, const ControlFlowGraph& inCFG)
	{
	ONoncontiguousByteBlockProtocol protocol;

		{
		OBinaryStream stream(protocol);

		CompilerCacheDuplicatingSerializer serializer(stream);

		serializer.serialize(inCFG);
		}

	mBytesStored += protocol.position();
	constexpr uword_t SIZE = 20 * 1024 * 1024;
	if (mBytesStored > mLogThreshold)
		{
		mLogThreshold = mBytesStored + SIZE;
		}
	mStore.set(inKey, protocol.getData());
	}
