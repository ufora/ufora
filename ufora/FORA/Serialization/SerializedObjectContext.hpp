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

#include "MemoizableDuringSerialization.hpp"
#include "ForaValueSerializationStream.hppml"
#include "../../core/PolymorphicSharedPtr.hpp"
#include "../../core/containers/MapWithIndex.hpp"
#include "../Vector/VectorDataID.hppml"
#include "../Vector/MutableVectorRecord.hppml"
#include "../TypedFora/ABI/VectorRecord.hpp"
#include "../TypedFora/ABI/VectorHandle.hpp"
#include "../Core/CSTValue.hppml"
#include "../Core/ClassMediator.hppml"
#include "../ControlFlowGraph/ControlFlowGraph.hppml"
#include "../Language/Function.hppml"

/***************
SerializedObjectContext

A context object that must be pushed onto the stack before FORA
values can be serialized.
****************/

namespace Fora {

class Pagelet;

}

namespace Cumulus {

class ComputationDefiniton;

}

class SerializedObjectContextSerializer;
class SerializedObjectContextDeserializer;
class SerializedObject;

class SerializedObjectContext : 
		public PolymorphicSharedPtrBase<SerializedObjectContext>
{
public:
		SerializedObjectContext(PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM);

		SerializedObjectContext(
				PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM,
				PolymorphicSharedPtr<SerializedObject> inObject
				);

		void	serialize(SerializedObjectContextSerializer& serializer, const Type& inVal);
		void	serialize(SerializedObjectContextSerializer& serializer, const JudgmentOnValue& inVal);
		void	serialize(SerializedObjectContextSerializer& serializer, const Expression& inVal);
		void	serialize(SerializedObjectContextSerializer& serializer, const ControlFlowGraph& inVal);
		void	serialize(SerializedObjectContextSerializer& serializer, const MutableVectorRecord& inVal);
		
		template<class T>
		void serialize(SerializedObjectContextSerializer& serializer, const T& in)
			{
			mMemoStorage.serialize(serializer, in, false);
			}

		//deserialize a FORA value.  
		void	deserialize(SerializedObjectContextDeserializer& deserializer, Type& outVal);
		void	deserialize(SerializedObjectContextDeserializer& deserializer, JudgmentOnValue& outVal);
		void	deserialize(SerializedObjectContextDeserializer& deserializer, Expression& outVal);
		void	deserialize(SerializedObjectContextDeserializer& deserializer, ControlFlowGraph& outVal);
		void	deserialize(SerializedObjectContextDeserializer& deserializer, MutableVectorRecord& outVal);
		
		template<class T>
		void deserialize(SerializedObjectContextDeserializer& deserializer, T& out)
			{
			mMemoStorage.deserialize(deserializer, out, false);
			}

		static SerializedObjectContext& currentContext();

		PolymorphicSharedPtr<VectorDataMemoryManager> getVDMM() const
			{
			return mVDMM;
			}
private:
		PolymorphicSharedPtr<VectorDataMemoryManager> mVDMM;

		MapWithIndex<Type, uint32_t> mTypesReferenced;

		MapWithIndex<JOV, uint32_t> mJovsReferenced;

		MapWithIndex<Expression, uint32_t> mExpressionsReferenced;

		MapWithIndex<ControlFlowGraph, uint32_t> mControlFlowGraphsReferenced;

		MapWithIndex<MutableVectorRecord, uint32_t> mMutableVectorRecordsSerialized;

		Fora::MemoizableDuringSerialization::MemoStorage mMemoStorage;
		
		friend class SerializedObject;
};

//serializer to use when serializing FORA values.
class SerializedObjectContextSerializer : public Fora::ForaValueSerializationStream {
public:
		SerializedObjectContextSerializer(	OBinaryStream& s, 
											SerializedObjectContext& context
											) : 
				Fora::ForaValueSerializationStream(s),
				mContext(context)
			{
			}

		void serialize(const Type& in)
			{
			mContext.serialize(*this, in);
			}

		void serialize(const JOV& in)
			{
			mContext.serialize(*this, in);
			}

		void serialize(const Expression& in)
			{
			mContext.serialize(*this, in);
			}

		void serialize(const ControlFlowGraph& in)
			{
			mContext.serialize(*this, in);
			}

		void serialize(const MutableVectorRecord& in)
			{
			mContext.serialize(*this, in);
			}

		void serialize(const Cumulus::ComputationDefinitionTerm& in);

		void serialize(const TypedFora::Abi::VectorHandlePtr& in);

		void serialize(const boost::shared_ptr<Fora::Pagelet>& in);

		SerializedObjectContext& getContext(void) const
			{
			return mContext;
			}
	
		template<class T>
		void serialize(const T& in)
			{
			Serializer<T, ForaValueSerializationStream>::serialize(*this, in);
			}

private:
		SerializedObjectContext& mContext;
};


class SerializedObjectContextDeserializer : public Fora::ForaValueDeserializationStream {
public:
		SerializedObjectContextDeserializer(IBinaryStream& s, 
											SerializedObjectContext& context,
											MemoryPool* inTargetMemoryPool
											) : 
				Fora::ForaValueDeserializationStream(s, inTargetMemoryPool, context.getVDMM()),
				mContext(context)
			{
			}

		void deserialize(Type& out)
			{
			mContext.deserialize(*this, out);
			}

		void deserialize(JOV& out)
			{
			mContext.deserialize(*this, out);
			}

		void deserialize(Expression& out)
			{
			mContext.deserialize(*this, out);
			}

		void deserialize(ControlFlowGraph& out)
			{
			mContext.deserialize(*this, out);
			}

		void deserialize(MutableVectorRecord& out)
			{
			mContext.deserialize(*this, out);
			}

		void deserialize(Cumulus::ComputationDefinitionTerm& out);

		void deserialize(TypedFora::Abi::VectorHandlePtr& in);

		void deserialize(boost::shared_ptr<Fora::Pagelet>& in);

		template<class T>
		void deserialize(T& out)
			{
			Deserializer<T, ForaValueDeserializationStream>::deserialize(*this, out);
			}

		SerializedObjectContext& getContext(void) const
			{
			return mContext;
			}
private:
		SerializedObjectContext& mContext;
};

template<class T>
SerializedObjectContextSerializer& operator<<(SerializedObjectContextSerializer& s, const T& t)
	{
	Serializer<T, SerializedObjectContextSerializer>::serialize(s,t);
	return s;
	}

template<class T>
SerializedObjectContextDeserializer& operator>>(SerializedObjectContextDeserializer& s, T& t)
	{
	Deserializer<T, SerializedObjectContextDeserializer>::deserialize(s,t);
	return s;
	}


