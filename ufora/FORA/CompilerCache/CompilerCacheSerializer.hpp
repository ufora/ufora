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
#pragma once

#include "../Serialization/ForaValueSerializationStream.hppml"

class MemoizableObject;
class ObjectIdentifier;
class OnDiskCompilerStore;

/// Duplicating, as opposed to Memoizing
class CompilerCacheDuplicatingSerializer : public Fora::ForaValueSerializationStream {
public:
	CompilerCacheDuplicatingSerializer(
			//the stream we’re writing nonmemoized bytes to
			OBinaryStream& inStream
			) :
			ForaValueSerializationStream(inStream)
		{}

	void serialize(const Type& inType);

	void serialize(const JudgmentOnValue& inJOV);

	void serialize(const Expression& inExpr);

	void serialize(const ControlFlowGraph& inCFG);

	void serialize(const MutableVectorRecord& in) {}

	void serialize(const Cumulus::ComputationDefinitionTerm& in) {}

	void serialize(TypedFora::Abi::VectorHandlePtr const& in) {}

	void serialize(const boost::shared_ptr<Fora::Pagelet>& in) {}

	using Fora::ForaValueSerializationStream::serialize;

};


/// Duplicating, as opposed to Memoizing
class CompilerCacheDuplicatingDeserializer : public Fora::ForaValueDeserializationStream {
public:
	CompilerCacheDuplicatingDeserializer(
			//the stream we’re writing nonmemoized bytes to
			IBinaryStream& inStream,
			//disk cache we’re storing memoized objects in
			MemoryPool* inMemPool,
			PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM
			) :
			ForaValueDeserializationStream(inStream, inMemPool, inVDMM)
		{}

	void deserialize(Type& outType);

	void deserialize(JudgmentOnValue& outJOV);

	void deserialize(Expression& outExpr);

	void deserialize(ControlFlowGraph& outCFG);

	void deserialize(MutableVectorRecord& out) {}

	void deserialize(Cumulus::ComputationDefinitionTerm& out) {}

	void deserialize(TypedFora::Abi::VectorHandlePtr& out) {}

	void deserialize(boost::shared_ptr<Fora::Pagelet>& out) {}

	using Fora::ForaValueDeserializationStream::deserialize;

};

class CompilerCacheMemoizingBufferedSerializer : public Fora::ForaValueSerializationStream {
public:
	CompilerCacheMemoizingBufferedSerializer(
			//the stream we’re writing bytes to
			OBinaryStream& inStream,
			const OnDiskCompilerStore& store
			);

	void serialize(const Type& inType);

	void serialize(const JudgmentOnValue& inJOV);

	void serialize(const Expression& inExpr);

	void serialize(const ControlFlowGraph& inCFG);

	void serialize(const MutableVectorRecord& in) {}

	void serialize(const Cumulus::ComputationDefinitionTerm& in) {}

	void serialize(TypedFora::Abi::VectorHandlePtr const& in) {}

	void serialize(const boost::shared_ptr<Fora::Pagelet>& in) {}

	using Fora::ForaValueSerializationStream::serialize;

	shared_ptr<map<ObjectIdentifier, MemoizableObject> > getStoredObjectMap() { return mStoredObjectMap; }

private:
	template<class T>
	void serializeWithMemoization(const T& inObj);

private:
	shared_ptr<map<ObjectIdentifier, MemoizableObject> > mStoredObjectMap;
	const OnDiskCompilerStore& mObjectStore;
};

class CompilerCacheMemoizingBufferedDeserializer : public Fora::ForaValueDeserializationStream {
public:
	CompilerCacheMemoizingBufferedDeserializer(
			//the stream we’re writing nonmemoized bytes to
			IBinaryStream& inStream,
			//disk cache we’re storing memoized objects in
			MemoryPool* inMemPool,
			PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM,
			OnDiskCompilerStore& store
			);

	void deserialize(Type& outType);

	void deserialize(JudgmentOnValue& outJOV);

	void deserialize(Expression& inExpr);

	void deserialize(ControlFlowGraph& outCFG);

	void deserialize(MutableVectorRecord& out) {}

	void deserialize(Cumulus::ComputationDefinitionTerm& out) {}

	void deserialize(TypedFora::Abi::VectorHandlePtr& out) {}

	void deserialize(boost::shared_ptr<Fora::Pagelet>& out) {}

	using Fora::ForaValueDeserializationStream::deserialize;

	shared_ptr<map<ObjectIdentifier, MemoizableObject> > getRestoredObjectMap() { return mRestoredObjectMap; }

private:
	template<class T>
	void deserializeWithMemoization(T& outObj);

private:
	OnDiskCompilerStore& mObjectStore;
	shared_ptr<map<ObjectIdentifier, MemoizableObject> > mRestoredObjectMap;
	bool mIsRoot;
};

