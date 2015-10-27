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

#include <string>
#include "MemoizableDuringSerialization.hpp"
#include "../../core/PolymorphicSharedPtr.hpp"
#include "../../core/containers/MapWithIndex.hpp"
#include "../../core/serialization/NoncontiguousByteBlock.hpp"
#include "../../core/serialization/ONoncontiguousByteBlockProtocol.hpp"
#include "../../core/serialization/INoncontiguousByteBlockProtocol.hpp"
#include "VectorMemoizingForaValueSerializationStream.hppml"
#include "../Core/ImplVal.hppml"
#include "../Core/MemoryPool.hpp"
#include "../Core/Type.hppml"
#include "../Language/Function.hppml"
#include "../ControlFlowGraph/ControlFlowGraph.hppml"
#include "SerializedObjectContext.hpp"

class SerializedObjectFlattenerSerializer;
class SerializedObjectInflaterDeserializer;

/*************
SerializedObject 

Holds the result serializing some object graph that has references to
FORA values objects. The data holds the references by index
in the order in which they were encountered
**************/

class SerializedObject : public PolymorphicSharedPtrBase<SerializedObject> {
public:
		typedef PolymorphicSharedPtr<SerializedObject> pointer_type;
		
		SerializedObject();

		~SerializedObject();
		
		//create a SerializedObject that has no external dependencies whatsoever
		SerializedObject(		const PolymorphicSharedPtr<NoncontiguousByteBlock>& inSerializedData);

		SerializedObject(		const PolymorphicSharedPtr<NoncontiguousByteBlock>& inSerializedData, 
								const PolymorphicSharedPtr<SerializedObjectContext>& inContext
								);
		
		SerializedObject&	operator=(const SerializedObject& in);

		static PolymorphicSharedPtr<SerializedObject> fromByteBlock(
				const PolymorphicSharedPtr<NoncontiguousByteBlock>& inString
				);

		hash_type	hash(void) const;

		const PolymorphicSharedPtr<NoncontiguousByteBlock>&	getSerializedData();

		template<class T>
		static PolymorphicSharedPtr<SerializedObject> serialize(
			const T& inElt, 
			PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM
			);

		template<class T>
		static void	deserialize(
						const PolymorphicSharedPtr<SerializedObject>& inObject,
						PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM,
						T& outVal
						);


		template<class serializer_type>
		static void serialize(	serializer_type& s, 
								const SerializedObject& t)
			{
			s.serialize(*t.mSerializedData);
			s.serialize(t.mTypesReferenced);
			s.serialize(t.mJovsReferenced);
			s.serialize(t.mExpressionsReferenced);
			s.serialize(t.mControlFlowGraphsReferenced);
			s.serialize(t.mMemoStorage);
			}

		template<class serializer_type>
		static void deserialize(	serializer_type& s, 
									SerializedObject& t)
			{
			t.mSerializedData.reset(new NoncontiguousByteBlock);

			s.deserialize(*t.mSerializedData);
			s.deserialize(t.mTypesReferenced);
			s.deserialize(t.mJovsReferenced);
			s.deserialize(t.mExpressionsReferenced);
			s.deserialize(t.mControlFlowGraphsReferenced);
			s.deserialize(t.mMemoStorage);
			}

		std::string toString(void) const;

		long totalValues(void) const;
private:
		Fora::MemoizableDuringSerialization::MemoStorage mMemoStorage;
		
		PolymorphicSharedPtr<NoncontiguousByteBlock> mSerializedData;
		
		MapWithIndex<Type, uint32_t> mTypesReferenced;
		
		MapWithIndex<JudgmentOnValue, uint32_t> mJovsReferenced;

		MapWithIndex<Expression, uint32_t> mExpressionsReferenced;
		
		MapWithIndex<ControlFlowGraph, uint32_t> mControlFlowGraphsReferenced;

		mutable Nullable<hash_type> mHash;

		friend class SerializedObjectContext;

		friend class SerializedObjectFlattenerSerializer;

		friend class SerializedObjectInflaterDeserializer;
		
		template<class T, class serializer_type>
		friend class Serializer;
		
		template<class T, class serializer_type>
		friend class Deserializer;
};


template<>
class CPPMLEquality<PolymorphicSharedPtr<SerializedObject>, void> {
public:
		static char cmp(	const PolymorphicSharedPtr<SerializedObject>& lhs,
							const PolymorphicSharedPtr<SerializedObject>& rhs
							)
			{
			return lhs->hash().cmp(rhs->hash());
			}
};

template<class serializer_type>
class Serializer<PolymorphicSharedPtr<SerializedObject>, serializer_type> {
public:
		static void serialize(	serializer_type& s, 
								const PolymorphicSharedPtr<SerializedObject>& t)
			{
			if (!t)
				s.serialize(false);
			else
				{
				s.serialize(true);
				s.serialize(*t);	
				}
			}
};

template<class serializer_type>
class Deserializer<PolymorphicSharedPtr<SerializedObject>, serializer_type> {
public:
		static void deserialize(serializer_type& s, 
								PolymorphicSharedPtr<SerializedObject>& t)
			{
			bool hasOne;
			s.deserialize(hasOne);

			if (hasOne)
				{
				t.reset(new SerializedObject());
				s.deserialize(*t);
				}
			}
};

template<class serializer_type>
class Serializer<SerializedObject, serializer_type> {
public:
		static void serialize(	serializer_type& s, const SerializedObject& t)
			{
			SerializedObject::serialize(s,t);
			}
};

template<class serializer_type>
class Deserializer<SerializedObject, serializer_type> {
public:
		static void deserialize(serializer_type& s, SerializedObject& t)
			{
			SerializedObject::deserialize(s,t);
			}
};

template<class T>
PolymorphicSharedPtr<SerializedObject> 
SerializedObject::serialize(const T& inElt, PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM)
	{
	PolymorphicSharedPtr<SerializedObjectContext> context;
	context.reset(new SerializedObjectContext(inVDMM));
	
	ONoncontiguousByteBlockProtocol				protocol;

		{
		OBinaryStream stream(protocol);
	
		SerializedObjectContextSerializer serializer(stream, *context);

		Fora::VectorMemoizingForaValueSerializationStream valueStream(serializer);

		valueStream.serialize(inElt);
		}
	
	return PolymorphicSharedPtr<SerializedObject>(
		new SerializedObject(
			protocol.getData(),
			context
			)
		);
	}

template<class T>
void	SerializedObject::deserialize(
						const PolymorphicSharedPtr<SerializedObject>& inObject,
						PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM,
						T& outVal
						)
	{
	INoncontiguousByteBlockProtocol	protocol(inObject->getSerializedData());

	PolymorphicSharedPtr<SerializedObjectContext> context(
		new SerializedObjectContext(inVDMM, inObject)
		);
	
	IBinaryStream stream(protocol);

	SerializedObjectContextDeserializer deserializer(
		stream, 
		*context, 
		MemoryPool::getFreeStorePool()
		);

	Fora::VectorMemoizingForaValueDeserializationStream valueStream(deserializer);

	valueStream.deserialize(outVal);
	}

class HashingStreamSerializer;

template<>
class Serializer<SerializedObject, HashingStreamSerializer> {
public:
		static void serialize(HashingStreamSerializer& s, const SerializedObject& in);
};

template<>
class Serializer<PolymorphicSharedPtr<SerializedObject>, HashingStreamSerializer> {
public:
		static void serialize(HashingStreamSerializer& s, const PolymorphicSharedPtr<SerializedObject>& in);
};


template<>
class CPPMLPrettyPrint<PolymorphicSharedPtr<SerializedObject> > {
public:
		static void prettyPrint(CPPMLPrettyPrintStream& s, const PolymorphicSharedPtr<SerializedObject>& t)
			{
			if (t)
				streamTo(s, "SerializedObject(" + prettyPrintString(t->hash()) + ")");
			else
				streamTo(s, "SerializedObject(<null>)");
			}
};


template<class T, class T2>
class CPPMLTransform;

template<>
class CPPMLTransform<PolymorphicSharedPtr<SerializedObject>, void> {
public:
		template<class F>
		static Nullable<PolymorphicSharedPtr<SerializedObject> > apply(
							const PolymorphicSharedPtr<SerializedObject>& in, 
							const F& f
							)
			{
			return null();
			}
};





