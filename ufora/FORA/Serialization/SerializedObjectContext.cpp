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
#include "SerializedObjectContext.hpp"
#include "SerializedObjectFlattener.hpp"
#include "../../core/debug/StackTrace.hpp"
#include "../../core/threading/ScopedThreadLocalContext.hpp"
#include "ForaValueSerializationStream.hppml"
#include "../../cumulus/ComputationDefinition.hppml"
#include "../VectorDataManager/PageletTree.hppml"
#include "../TypedFora/ABI/ForaValueArray.hppml"


SerializedObjectContext::SerializedObjectContext(PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM) :
		mVDMM(inVDMM)
	{
	}

SerializedObjectContext::SerializedObjectContext(
									PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM,
									PolymorphicSharedPtr<SerializedObject> inObject
									) :
		mTypesReferenced(inObject->mTypesReferenced),
		mJovsReferenced(inObject->mJovsReferenced),
		mExpressionsReferenced(inObject->mExpressionsReferenced),
		mControlFlowGraphsReferenced(inObject->mControlFlowGraphsReferenced),
		mMemoStorage(inObject->mMemoStorage),
		mVDMM(inVDMM)
	{
	}
SerializedObjectContext&		SerializedObjectContext::currentContext()
	{
	typedef Ufora::threading::ScopedThreadLocalContext<
							PolymorphicSharedPtr<SerializedObjectContext> > context_type;

	lassert_dump(context_type::has(),
		"SerializedObjectContext context not set. "
		"Please use 'with ufora.native.FORA.SerializedObjectContextSetter' "
		"to push one before pickling"
		);
	return *context_type::get();
	}


namespace {

//return the index of 'inVal' in 'map'. add it at the end if it's not there.
template<class map_type, class T>
uint32_t	addToIndex(map_type& inMap, const T& inVal)
	{
	if (inMap.hasKey(inVal))
		return inMap.getValue(inVal);

	//not there. add it on the end
	uint32_t index = inMap.size();
	inMap.set(inVal, index);
	return index;
	}

template<class map_type>
auto lookupInIndex(const map_type& inMap, uint32_t inVal) -> decltype(*inMap.getKeys(inVal).begin())
	{
	const auto& keys(inMap.getKeys(inVal));

	if (!keys.size())
		throw standardLogicErrorWithStacktrace("corrupt SerializedObjectContext: unknown object ID");
	if (keys.size() != 1)
		throw standardLogicErrorWithStacktrace("corrupt SerializedObjectContext: index had multiple keys");
	return *keys.begin();
	}


}

void	SerializedObjectContext::serialize(SerializedObjectContextSerializer& serializer, const JOV& inVal)
	{
	serializer.serialize(addToIndex(mJovsReferenced, inVal));
	}

void	SerializedObjectContext::serialize(SerializedObjectContextSerializer& serializer, const Type& inVal)
	{
	serializer.serialize(addToIndex(mTypesReferenced, inVal));
	}

void	SerializedObjectContext::serialize(SerializedObjectContextSerializer& serializer, const Expression& inVal)
	{
	serializer.serialize(addToIndex(mExpressionsReferenced, inVal));
	}

void	SerializedObjectContext::serialize(SerializedObjectContextSerializer& serializer, const ControlFlowGraph& inVal)
	{
	serializer.serialize(addToIndex(mControlFlowGraphsReferenced, inVal));
	}

void	SerializedObjectContext::serialize(SerializedObjectContextSerializer& serializer, const MutableVectorRecord& vecRecord)
	{
	if (mMutableVectorRecordsSerialized.hasKey(vecRecord))
		{
		serializer.serialize(mMutableVectorRecordsSerialized.getValue(vecRecord));
		return;
		}

	uint32_t newIndex = addToIndex(mMutableVectorRecordsSerialized, vecRecord);
	serializer.serialize(newIndex);

	Serializer<MutableVectorRecord,
			   Fora::ForaValueSerializationStream>::serialize(serializer, vecRecord);
	}

//deserialize a FORA value.
void	SerializedObjectContext::deserialize(SerializedObjectContextDeserializer& deserializer, Type& outType)
	{
	uint32_t index;
	deserializer.deserialize(index);

	outType = lookupInIndex(mTypesReferenced, index);
	}

void	SerializedObjectContext::deserialize(SerializedObjectContextDeserializer& deserializer, JOV& outType)
	{
	uint32_t index;
	deserializer.deserialize(index);

	outType = lookupInIndex(mJovsReferenced, index);
	}

void	SerializedObjectContext::deserialize(SerializedObjectContextDeserializer& deserializer, Expression& out)
	{
	uint32_t index;
	deserializer.deserialize(index);

	out = lookupInIndex(mExpressionsReferenced, index);
	}

void	SerializedObjectContext::deserialize(SerializedObjectContextDeserializer& deserializer, ControlFlowGraph& out)
	{
	uint32_t index;
	deserializer.deserialize(index);

	out = lookupInIndex(mControlFlowGraphsReferenced, index);
	}

void	SerializedObjectContext::deserialize(SerializedObjectContextDeserializer& deserializer, MutableVectorRecord& vecRecord)
	{
	uint32_t index;
	deserializer.deserialize(index);

	if (mMutableVectorRecordsSerialized.hasValue(index))
		{
		const auto& keys(mMutableVectorRecordsSerialized.getKeys(index));
		lassert(keys.size() == 1);

		vecRecord = *keys.begin();
		return;
		}

	Deserializer<MutableVectorRecord,
				 Fora::ForaValueDeserializationStream>::deserialize(deserializer, vecRecord);

	mMutableVectorRecordsSerialized.set(vecRecord, index);
	}

void SerializedObjectContextSerializer::serialize(const Cumulus::ComputationDefinitionTerm& in)
	{
	mContext.serialize(*this, in);
	}

void SerializedObjectContextDeserializer::deserialize(Cumulus::ComputationDefinitionTerm& out)
	{
	mContext.deserialize(*this, out);
	}

void SerializedObjectContextSerializer::serialize(TypedFora::Abi::VectorHandlePtr const& in)
	{
	Serializer<TypedFora::Abi::VectorHandlePtr, Fora::ForaValueSerializationStream>::serialize(*this, in);
	}

void SerializedObjectContextDeserializer::deserialize(TypedFora::Abi::VectorHandlePtr& out)
	{
	Deserializer<TypedFora::Abi::VectorHandlePtr, Fora::ForaValueDeserializationStream>::deserialize(*this, out);
	}

void SerializedObjectContextSerializer::serialize(boost::shared_ptr<Fora::Pagelet> const& in)
	{
	Ufora::threading::ScopedThreadLocalContext<Fora::Interpreter::ExecutionContext> setECContextToNull;

	Fora::VectorMemoizingForaValueSerializationStream stream(*this);

	Serializer<TypedFora::Abi::ForaValueArray,
		Fora::ForaValueSerializationStream>::serialize(stream, *in->getValues());
	}

void SerializedObjectContextDeserializer::deserialize(boost::shared_ptr<Fora::Pagelet>& out)
	{
	double t0 = curClock();
	static double timeElapsed = 0;
	static double totalBytes = 0;

	lassert_dump(getVDMM(), "can't deserialize a Pagelet without a VDMM");

	out.reset(new Fora::Pagelet(getVDMM()));

	SerializedObjectContextDeserializer newDeserializer(getStream(), mContext, &*out);

		{
		Ufora::threading::ScopedThreadLocalContext<Fora::Interpreter::ExecutionContext> setECContextToNull;

		Fora::VectorMemoizingForaValueDeserializationStream stream(newDeserializer);

		Deserializer<TypedFora::Abi::ForaValueArray,
			Fora::ForaValueDeserializationStream>::deserialize(stream, *out->getValues());
		}

	out->freeze();

	double elapsed = curClock() - t0;

	totalBytes += out->totalBytesAllocated();

	if (int(elapsed+timeElapsed) != int(timeElapsed))
		LOG_INFO << timeElapsed + elapsed << " total spent deserializing Pagelets. "
			<< elapsed << " deserializing " << out->getValues()->size()
			<< " x " << out->getValues()->currentJor()
			<< ". MB/sec = " << totalBytes / 1024.0 / 1024.0 / (timeElapsed + elapsed)
			;

	timeElapsed += elapsed;
	}

