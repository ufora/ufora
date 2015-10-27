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

#include "../../core/PolymorphicSharedPtr.hpp"
#include "../../core/serialization/NoncontiguousByteBlock.hpp"
#include "../Core/MemoryPool.hpp"
#include "SerializedObject.hpp"
#include "SerializedObjectContext.hpp"
#include "ForaValueSerializationStream.hppml"
#include "../TypedFora/ABI/VectorRecord.hpp"

/*************
SerializedObjectFlattener

An object that "flattens" SerializedObject records into strings, 
along with another object that 'inflates' them back to SerializedObjects.

Objects must be passed to an inflater in the same order that they were passed
to the flattener.

***************/

class SerializedObjectInflater;
class SerializedObjectFlattenerSerializer;
class SerializedObjectInflaterDeserializer;
class VectorDataMemoryManager;

class SerializedObjectFlattener : 
		public PolymorphicSharedPtrBase<SerializedObjectFlattener>
{
public:
		SerializedObjectFlattener() :
				mMemoizedSize(0)
			{
			}
		
		template<class T>
		static PolymorphicSharedPtr<NoncontiguousByteBlock> serializeEntireObjectGraph(const T& in)
			{
			return flattenOnce(SerializedObject::serialize(in, PolymorphicSharedPtr<VectorDataMemoryManager>()));
			}

		PolymorphicSharedPtr<NoncontiguousByteBlock> flatten(const PolymorphicSharedPtr<SerializedObject>& inSPO);

		template<class T>
		PolymorphicSharedPtr<NoncontiguousByteBlock> flatten(const T& in)
			{
			return flatten(SerializedObject::serialize(in, PolymorphicSharedPtr<VectorDataMemoryManager>()));
			}

		//flatten an entire object graph. Creates a fresh flattener to do it.
		static PolymorphicSharedPtr<NoncontiguousByteBlock> flattenOnce(const PolymorphicSharedPtr<SerializedObject>& inSPO);

		static void flattenOnce(OBinaryStream& stream, const PolymorphicSharedPtr<SerializedObject>& inSerializedObject);
		
		void flatten(OBinaryStream& stream, const PolymorphicSharedPtr<SerializedObject>& inSerializedObject);

		uint32_t getMemoizedSize(void) const;

		//pretend that we and the other side have both just agreed that we have written/read
		//this type, even though we only exchanged hashes for it
		void considerValueAlreadyWritten(const ImplValContainer& inValue);

private:
		friend class SerializedObjectFlattenerSerializer;

		map<hash_type, uint32_t> mTypesReferenced;
		map<hash_type, uint32_t> mJovsReferenced;
		map<hash_type, uint32_t> mExpressionsReferenced;
		map<hash_type, uint32_t> mControlFlowGraphsReferenced;

		Fora::MemoizableDuringSerialization::MemoStorage mMemoStorage;

		uint32_t mMemoizedSize;

		friend class SerializedObjectInflater;
};


class SerializedObjectInflater : public PolymorphicSharedPtrBase<SerializedObjectInflater> {
public:
		SerializedObjectInflater();

		~SerializedObjectInflater();

		template<class T>
		static void deserializeEntireObjectGraph(
					const PolymorphicSharedPtr<NoncontiguousByteBlock>& inData,
					T& out
					)
			{
			PolymorphicSharedPtr<SerializedObject> serializedObject = 
							SerializedObjectInflater::inflateOnce(inData);

			SerializedObject::deserialize(
				serializedObject, 
				PolymorphicSharedPtr<VectorDataMemoryManager>(), 
				out
				);
			}
		
		template<class T>
		void inflate(PolymorphicSharedPtr<NoncontiguousByteBlock> data, T& out)
			{
			return SerializedObject::deserialize(
				inflate(data), 
				PolymorphicSharedPtr<VectorDataMemoryManager>(), 
				out
				);
			}

		PolymorphicSharedPtr<SerializedObject>	inflate(
					const PolymorphicSharedPtr<NoncontiguousByteBlock>& inFlattened
					);

		PolymorphicSharedPtr<SerializedObject>	inflate(
					const PolymorphicSharedPtr<NoncontiguousByteBlock>& inFlattened,
					PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM
					);

		//deflate an entire object graph by creating a fresh inflator. 
		static PolymorphicSharedPtr<SerializedObject> inflateOnce(
					const PolymorphicSharedPtr<NoncontiguousByteBlock>& inFlattened
					);

		PolymorphicSharedPtr<SerializedObject> inflate(IBinaryStream& stream);

		static PolymorphicSharedPtr<SerializedObject> inflateOnce(
										IBinaryStream& stream
										);

		void considerValueAlreadyRead(const ImplValContainer& inType);

private:
		friend class SerializedObjectInflaterDeserializer;

		MapWithIndex<Type, uint32_t> mTypesReferenced;

		MapWithIndex<JOV, uint32_t> mJovsReferenced;

		MapWithIndex<Expression, uint32_t> mExpressionsReferenced;
		
		MapWithIndex<ControlFlowGraph, uint32_t> mControlFlowGraphsReferenced;

		Fora::MemoizableDuringSerialization::MemoStorage mMemoStorage;
};

class SerializedObjectFlattenerSerializer : public Fora::ForaValueSerializationStream {
public:
		SerializedObjectFlattenerSerializer(
					SerializedObjectFlattener& in,
					OBinaryStream& stream
					) : 
				Fora::ForaValueSerializationStream(stream),
				mFlattener(in)
			{
			}

		template<class T>
		void serialize(const T& in)
			{
			Serializer<T, ForaValueSerializationStream>::serialize(*this, in);
			}

		template<class T>
		void serializeToMemoStorage(const T& in)
			{
			mFlattener.mMemoStorage.serialize(*(Fora::ForaValueSerializationStream*)this, in, true);
			}

		void serialize(const JOV& in);

		void serialize(const Type& in);

		void serialize(const Expression& in);

		void serialize(const ControlFlowGraph& in);

		void serialize(const MutableVectorRecord& in);

		void serialize(const Cumulus::ComputationDefinitionTerm& in);

		void serialize(TypedFora::Abi::VectorHandlePtr const& in);

		void serialize(const boost::shared_ptr<Fora::Pagelet>& in);

		SerializedObjectFlattener& getFlattener()
			{
			return mFlattener;
			}
private:
		SerializedObjectFlattener& mFlattener;
};

class SerializedObjectInflaterDeserializer : public Fora::ForaValueDeserializationStream {
public:
		SerializedObjectInflaterDeserializer(
						SerializedObjectInflater& in,
						IBinaryStream& stream,
						PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM,
						MemoryPool* targetPool = nullptr
						) : 
				Fora::ForaValueDeserializationStream(
					stream, 
					targetPool ? targetPool : MemoryPool::getFreeStorePool(), 
					inVDMM
					),
				mInflater(in),
				mTargetPool(targetPool)
			{
			if (mTargetPool == nullptr)
				mTargetPool = MemoryPool::getFreeStorePool();
			}

		MemoryPool* getTargetPool()
			{
			return mTargetPool;
			}

		template<class T>
		void deserializeFromMemoStorage(T& out)
			{
			mInflater.mMemoStorage.deserialize(
				*(Fora::ForaValueDeserializationStream*)this, 
				out, 
				true
				);
			}

		void deserialize(Type& out);

		void deserialize(JOV& out);

		void deserialize(Expression& out);

		void deserialize(ControlFlowGraph& out);

		void deserialize(MutableVectorRecord& out);

		void deserialize(Cumulus::ComputationDefinitionTerm& out);

		void deserialize(TypedFora::Abi::VectorHandlePtr& out);

		void deserialize(boost::shared_ptr<Fora::Pagelet>& in);

		template<class T>
		void deserialize(T& out)
			{
			Deserializer<T, ForaValueDeserializationStream>::deserialize(*this, out);
			}

		SerializedObjectInflater& getInflater()
			{
			return mInflater;
			}
private:
		MemoryPool* mTargetPool;

		SerializedObjectInflater& mInflater;
};
