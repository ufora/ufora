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
#include "SerializedObject.hpp"
#include "SerializedObjectContext.hpp"
#include "../../core/Logging.hpp"

SerializedObject::SerializedObject()
	{
	}

SerializedObject::SerializedObject(const PolymorphicSharedPtr<NoncontiguousByteBlock>& inSerializedData) :
		mSerializedData(inSerializedData)
	{
	}

SerializedObject::~SerializedObject()
	{
	}

SerializedObject::SerializedObject(	const PolymorphicSharedPtr<NoncontiguousByteBlock>& inSerializedData,
									const PolymorphicSharedPtr<SerializedObjectContext>& inContext
									) :
		mSerializedData(inSerializedData),
		mTypesReferenced(inContext->mTypesReferenced),
		mJovsReferenced(inContext->mJovsReferenced),
		mExpressionsReferenced(inContext->mExpressionsReferenced),
		mControlFlowGraphsReferenced(inContext->mControlFlowGraphsReferenced),
		mMemoStorage(inContext->mMemoStorage)
	{
	}

SerializedObject&	SerializedObject::operator=(const SerializedObject& in)
	{
	mSerializedData = in.mSerializedData;
	mTypesReferenced = in.mTypesReferenced;
	mJovsReferenced = in.mJovsReferenced;
	mExpressionsReferenced = in.mExpressionsReferenced;
	mControlFlowGraphsReferenced = in.mControlFlowGraphsReferenced;
	mMemoStorage = in.mMemoStorage;


	return *this;
	}

PolymorphicSharedPtr<SerializedObject>
SerializedObject::fromByteBlock(const PolymorphicSharedPtr<NoncontiguousByteBlock>& inBytes)
	{
	return PolymorphicSharedPtr<SerializedObject>(
		new SerializedObject(
			inBytes
			)
		);
	}

hash_type
SerializedObject::hash(void) const
	{
	if (!mHash)
		{
		hash_type h = (mSerializedData ? hashValue(*mSerializedData) : hash_type());

		h = h + hashValue(mTypesReferenced);
		h = h + hashValue(mJovsReferenced);
		h = h + hashValue(mExpressionsReferenced);
		h = h + hashValue(mControlFlowGraphsReferenced);
		h = h + mMemoStorage.hash();

		mHash = h;
		}

	return *mHash;
	}

const PolymorphicSharedPtr<NoncontiguousByteBlock>&
SerializedObject::getSerializedData()
	{
	return mSerializedData;
	}

void Serializer<SerializedObject, HashingStreamSerializer>::serialize(HashingStreamSerializer& s, const SerializedObject& in)
	{
	s.serialize(in.hash());
	}

void Serializer<PolymorphicSharedPtr<SerializedObject>, HashingStreamSerializer>::serialize(
				HashingStreamSerializer& s,
				const PolymorphicSharedPtr<SerializedObject>& in
				)
	{
	if (!in)
		s.serialize(hash_type(0));
	else
		{
		s.serialize(hash_type(1));
		s.serialize(in->hash());
		}
	}

std::string SerializedObject::toString(void) const
	{
	return "SerializedObject<bytes="
		+ boost::lexical_cast<string>(mSerializedData->totalByteCount())
		+ ", valcount=" + boost::lexical_cast<string>(totalValues())
		+ ", hash=" + hashToString(hash()) + ">"
		;
	}

long  SerializedObject::totalValues(void) const
	{
	return mTypesReferenced.size() +
		mJovsReferenced.size() +
		mExpressionsReferenced.size() +
		mControlFlowGraphsReferenced.size() +
		mMemoStorage.size()
		;
	}

