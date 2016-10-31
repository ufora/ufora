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
#include "../../core/InstanceCounter.hpp"

namespace Fora {
namespace MemoizableDuringSerialization {

class HashKeyFunction {
public:
	template<class T>
	hash_type operator()(const T& in) const
		{
		return hashValue(in);
		}
};

template<class T, class key_type = hash_type, class key_function = HashKeyFunction>
class MemoStorageBaseForSpecificType : public MemoStorageBase, InstanceCounter<MemoStorageBaseForSpecificType<T> > {
public:
	bool hasMemo(const void* inValuePtr) const
		{
		const T& inValue(*(const T*)(inValuePtr));

		return mIndices.find(mKeyFunction(inValue)) != mIndices.end();
		}

	void serialize(Fora::ForaValueSerializationStream& serializer) const
		{
		serializer.serialize(mValues);
		serializer.serialize(mIndices);
		serializer.serialize(mHash);
		}

	void deserialize(Fora::ForaValueDeserializationStream& serializer)
		{
		serializer.deserialize(mValues);
		serializer.deserialize(mIndices);
		serializer.deserialize(mHash);
		}

	uint32_t addMemoAndReturnIndex(const void* inValuePtr)
		{
		const T& inValue(*(const T*)(inValuePtr));

		key_type inKey = mKeyFunction(inValue);

		auto it = mIndices.find(inKey);

		lassert(it == mIndices.end());

		uint32_t newIndex = mIndices.size();

		mValues[newIndex] = inValue;

		mIndices[inKey] = newIndex;

		mHash = mHash + hashValue(inKey);

		return newIndex;
		}

	uint32_t getMemoIndex(const void* inValuePtr) const
		{
		const T& inValue(*(const T*)(inValuePtr));

		key_type inKey = mKeyFunction(inValue);

		auto it = mIndices.find(inKey);

		lassert(it != mIndices.end());

		return it->second;
		}

	bool hasMemo(uint32_t inIndex) const
		{
		return mValues.find(inIndex) != mValues.end();
		}

	const void* getMemo(uint32_t inIndex) const
		{
		return (const void*)&mValues.find(inIndex)->second;
		}

	void addMemo(uint32_t inIndex, const void* inValuePtr)
		{
		const T& inValue(*(const T*)(inValuePtr));

		key_type inKey = mKeyFunction(inValue);

		lassert(mValues.find(inIndex) == mValues.end());

		mValues[inIndex] = inValue;

		mIndices[inKey] = inIndex;

		mHash = mHash + hashValue(inKey);
		}

	virtual hash_type hash() const
		{
		return mHash;
		}

	virtual uint32_t size() const
		{
		return mValues.size();
		}

private:
	map<key_type, uint32_t> mIndices;

	map<uint32_t, T> mValues;

	hash_type mHash;

	key_function mKeyFunction;
};



template<class T, class memo_storage_type = MemoStorageBaseForSpecificType<T> >
class MemoStorageBaseRegistrar {
public:
	MemoStorageBaseRegistrar()
		{
		MemoStorageBaseRegistry::singleton().registerFactory(
			typeid(T).name(),
			boost::bind(&create)
			);
		}

	static MemoStorageBase* create()
		{
		return new memo_storage_type();
		}
};

}
}

