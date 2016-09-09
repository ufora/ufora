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
#include "CompilerCacheSerializer.hpp"
#include "MemoizableObject.hppml"
#include "ObjectIdentifier.hppml"
#include "OnDiskCompilerStore.hpp"
#include "../Core/ClassMediator.hppml"

class ControlFlowGraph;
class Expression;
class JudgmentOnValue;
class Type;

inline static
bool isMemoizable(const Expression& in)
	{
	return in.isCreateFunction()
			|| in.isCreateObject()
			|| in.isCreateClass();
	}

inline static
bool isMemoizable(const ControlFlowGraph& in) { return true; }

inline static
bool isMemoizable(const Type& in) { return true; }

inline static
bool isMemoizable(const JudgmentOnValue& in) { return true; }


void CompilerCacheDuplicatingSerializer::serialize(const Type& inType)
	{
	CPPMLSerializer<Type, Type::metadata>::serialize(*this, inType);
	}

void CompilerCacheDuplicatingSerializer::serialize(const JudgmentOnValue& inJOV)
	{
	CPPMLSerializer<JOV, JOV::metadata>::serialize(*this, inJOV);
	}

void CompilerCacheDuplicatingSerializer::serialize(const Expression& inExpr)
	{
	CPPMLSerializer<Expression, Expression::metadata>::serialize(*this, inExpr);
	}

void CompilerCacheDuplicatingSerializer::serialize(const ControlFlowGraph& inCFG)
	{
	CPPMLSerializer<ControlFlowGraph, ControlFlowGraph::metadata>::serialize(*this, inCFG);
	}


void CompilerCacheDuplicatingDeserializer::deserialize(Type& inType)
	{
	CPPMLSerializer<Type, Type::metadata>::deserialize(*this, inType);
	}

void CompilerCacheDuplicatingDeserializer::deserialize(JudgmentOnValue& inJOV)
	{
	CPPMLSerializer<JOV, JOV::metadata>::deserialize(*this, inJOV);
	}

void CompilerCacheDuplicatingDeserializer::deserialize(Expression& inExpr)
	{
	CPPMLSerializer<Expression, Expression::metadata>::deserialize(*this, inExpr);
	}

void CompilerCacheDuplicatingDeserializer::deserialize(ControlFlowGraph& inCFG)
	{
	CPPMLSerializer<ControlFlowGraph, ControlFlowGraph::metadata>::deserialize(*this, inCFG);
	}

CompilerCacheMemoizingBufferedSerializer::CompilerCacheMemoizingBufferedSerializer(
		//the stream we’re writing bytes to
		OBinaryStream& inStream,
		const OnDiskCompilerStore& store
		) :
		ForaValueSerializationStream(inStream),
		mObjectStore(store)
	{
	mStoredObjectMap.reset(new map<ObjectIdentifier, MemoizableObject>);
	}

template<class T>
void CompilerCacheMemoizingBufferedSerializer::serializeWithMemoization(const T& inObj)
	{
	ObjectIdentifier objId(makeObjectIdentifier(inObj));
	bool isMemo = isMemoizable(inObj);
	bool isAlreadySaved = false;
	if (isMemo && (
			mObjectStore.containsOnDisk(objId) ||
			mStoredObjectMap->find(objId) != mStoredObjectMap->end())
			)
		isAlreadySaved = true;

	Serializer<bool, CompilerCacheMemoizingBufferedSerializer>::serialize(*this, isAlreadySaved);
	if (isAlreadySaved)
		{
		CPPMLSerializer<ObjectIdentifier, ObjectIdentifier::metadata>::serialize(*this, objId);
		}
	else
		{
		CPPMLSerializer<T, typename T::metadata>::serialize(*this, inObj);
		if (isMemo)
			{
			mStoredObjectMap->insert(
					make_pair(objId, MemoizableObject::makeMemoizableObject(inObj))
					);
			}
		}
	}

void CompilerCacheMemoizingBufferedSerializer::serialize(const Type& inType)
	{
	serializeWithMemoization(inType);
	}

void CompilerCacheMemoizingBufferedSerializer::serialize(const JudgmentOnValue& inJOV)
	{
	serializeWithMemoization(inJOV);
	}

void CompilerCacheMemoizingBufferedSerializer::serialize(const Expression& inExpr)
	{
	serializeWithMemoization(inExpr);
	}

void CompilerCacheMemoizingBufferedSerializer::serialize(const ControlFlowGraph& inCFG)
	{
	serializeWithMemoization(inCFG);
	}


CompilerCacheMemoizingBufferedDeserializer::CompilerCacheMemoizingBufferedDeserializer(
		//the stream we’re writing nonmemoized bytes to
		IBinaryStream& inStream,
		//disk cache we’re storing memoized objects in
		MemoryPool* inMemPool,
		PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM,
		OnDiskCompilerStore& store
		) :
		ForaValueDeserializationStream(inStream, inMemPool, inVDMM),
		mObjectStore(store),
		mIsRoot(true)
	{
	mRestoredObjectMap.reset(new map<ObjectIdentifier, MemoizableObject>);
	}

template<class T>
void CompilerCacheMemoizingBufferedDeserializer::deserializeWithMemoization(T& outObj)
	{
	bool isRoot = mIsRoot;
	mIsRoot = false;
	bool isObjId;
	Deserializer<bool, CompilerCacheMemoizingBufferedDeserializer>::deserialize(*this, isObjId);
	if (!isObjId)
		{
		CPPMLSerializer<T, typename T::metadata>::deserialize(*this, outObj);
		if (!isRoot && isMemoizable(outObj))
			{
			ObjectIdentifier objId = makeObjectIdentifier(outObj);
			mRestoredObjectMap->insert(
					make_pair(objId, MemoizableObject::makeMemoizableObject(outObj))
					);
			}
		}
	else
		{
		ObjectIdentifier objId;
		CPPMLSerializer<ObjectIdentifier, ObjectIdentifier::metadata>::deserialize(*this, objId);

		auto it = mRestoredObjectMap->find(objId);
		if (it != mRestoredObjectMap->end())
			{
			outObj = (*it).second.extract<T>();
			}
		else
			{
			auto obj = mObjectStore.lookup<T>(objId);
			lassert_dump(obj, "deserialization failed");
			outObj = *obj;
			}
		}
	mIsRoot = isRoot;
	}

void CompilerCacheMemoizingBufferedDeserializer::deserialize(Type& outType)
	{
	deserializeWithMemoization(outType);
	}

void CompilerCacheMemoizingBufferedDeserializer::deserialize(JudgmentOnValue& outJOV)
	{
	deserializeWithMemoization(outJOV);
	}

void CompilerCacheMemoizingBufferedDeserializer::deserialize(Expression& outExpr)
	{
	deserializeWithMemoization(outExpr);
	}

void CompilerCacheMemoizingBufferedDeserializer::deserialize(ControlFlowGraph& outCFGF)
	{
	deserializeWithMemoization(outCFGF);
	}
