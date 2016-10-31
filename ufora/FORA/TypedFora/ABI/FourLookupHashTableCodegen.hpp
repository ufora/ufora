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

#include "FourLookupHashTable.hpp"

#include "../../Native/NativeCode.hppml"
#include "../../Native/TypedNativeExpression.hppml"
#include "../../Native/TypedNativeLibraryFunction.hpp"
#include "../../../core/Platform.hpp"

template<class T>
class NativeTypeForImpl;

template<class key_type, class value_type, bool threadsafe>
class NativeTypeForImpl<
			TypedFora::Abi::FourLookupHashTable<key_type, value_type, threadsafe> > {
public:
	typedef TypedFora::Abi::FourLookupHashTable<key_type, value_type, threadsafe> table_type;

	static NativeType get(void)
		{
		NativeType hashTableBody =
			NativeType::Composite("mKeys", NativeTypeFor<key_type>::get().ptr()) +
			NativeType::Composite("mValues", NativeTypeFor<value_type>::get().ptr()) +
			NativeType::Composite("mBucketCount", NativeTypeFor<size_t>::get()) +
			NativeType::Composite("mElementCount", NativeTypeFor<size_t>::get())
			;

		return
			NativeType::Composite("mTablePtr", hashTableBody.ptr()) +
			NativeType::Composite(
				NativeType::Array(
					NativeType::Integer(8,false),
					sizeof(table_type) - hashTableBody.ptr().packedSize()
					)
				)
			;
		}
};

template<class key_type, class value_type, bool threadsafe>
class TypedNativeExpressionBehaviors<
	TypedFora::Abi::FourLookupHashTable<key_type, value_type, threadsafe>*
	>
{
public:
	typedef TypedFora::Abi::FourLookupHashTable<key_type, value_type, threadsafe> table_type;
	typedef TypedFora::Abi::UnresizableFourLookupHashTable<key_type, value_type> inner_table_type;


	TypedNativeExpressionBehaviors(NativeExpression e) : mThis(e)
		{
		}

	TypedNativeExpression<table_type*> self() const
		{
		return TypedNativeExpression<table_type*>(mThis);
		}

	TypedNativeExpression<size_t> size() const
		{
		return TypedNativeExpression<size_t>(mThis["mTablePtr"].load()["mElementCount"].load());
		}

    #ifdef BSA_PLATFORM_APPLE
	TypedNativeExpression<unsigned long long> bucketCount() const
		{
		return TypedNativeExpression<unsigned long long>(mThis["mTablePtr"].load()["mBucketCount"].load());
		}
    #else
	TypedNativeExpression<size_t> bucketCount() const
		{
		return TypedNativeExpression<size_t>(mThis["mTablePtr"].load()["mBucketCount"].load());
		}
    #endif

	TypedNativeExpression<key_type*> keys() const
		{
		return TypedNativeExpression<key_type*>(mThis["mTablePtr"].load()["mKeys"].load());
		}

	TypedNativeExpression<value_type*> values() const
		{
		return TypedNativeExpression<value_type*>(mThis["mTablePtr"].load()["mValues"].load());
		}

	TypedNativeExpression<sword_t> slotFor(TypedNativeExpression<key_type> key, sword_t index) const
		{
		sword_t whichPrime = inner_table_type::PRIME_4;
		if (index == 0)
			whichPrime = inner_table_type::PRIME_1;
		if (index == 1)
			whichPrime = inner_table_type::PRIME_2;
		if (index == 2)
			whichPrime = inner_table_type::PRIME_3;

		return (key * key_type(whichPrime) + key_type(1)) %
			((TypedNativeExpression<key_type>)bucketCount());
		}

	TypedNativeExpression<sword_t> slotFor(TypedNativeExpression<key_type> key) const
		{
		TypedNativeVariable<sword_t> v1;
		TypedNativeVariable<sword_t> v2;
		TypedNativeVariable<sword_t> v3;
		TypedNativeVariable<sword_t> v4;

		using namespace TypedNativeExpressionHelpers;

		return
			let(v1, slotFor(key, 0),
			if_(keys()[v1] == key, v1,
			let(v2, slotFor(key, 1),
			if_(keys()[v2] == key, v2,
			let(v3, slotFor(key, 2),
			if_(keys()[v3] == key, v3,
			let(v4, slotFor(key, 3),
			if_(keys()[v4] == key, v4,
				TypedNativeExpression<sword_t>(-1)
				))))))));
		}

	TypedNativeExpression<value_type> valueForSlot(TypedNativeExpression<sword_t> slot) const
		{
		return values()[slot];
		}

	TypedNativeExpression<key_type> keyForSlot(TypedNativeExpression<sword_t> slot) const
		{
		return keys()[slot];
		}

	TypedNativeExpression<sword_t> slotForOrInsertionPoint(TypedNativeExpression<key_type> key) const
		{
		TypedNativeVariable<sword_t> v1;
		TypedNativeVariable<sword_t> v2;
		TypedNativeVariable<sword_t> v3;
		TypedNativeVariable<sword_t> v4;

		using namespace TypedNativeExpressionHelpers;

		return
			let(v1, slotFor(key, 0),
			if_(keys()[v1] == key || keys()[v1] == (key_type)0, v1,
			let(v2, slotFor(key, 1),
			if_(keys()[v2] == key || keys()[v2] == (key_type)0, v2,
			let(v3, slotFor(key, 2),
			if_(keys()[v3] == key || keys()[v3] == (key_type)0, v3,
			let(v4, slotFor(key, 3),
			if_(keys()[v4] == key || keys()[v4] == (key_type)0, v4,
				TypedNativeExpression<sword_t>(-1)
				))))))));
		}

	TypedNativeExpression<void> insert(
									TypedNativeExpression<key_type> key,
									TypedNativeExpression<value_type> value
									) const
		{
		TypedNativeVariable<sword_t> slot;

		using namespace TypedNativeExpressionHelpers;

		auto insertFunction = makeTypedNativeLibraryFunction(&table_type::staticInsertFunction);

		if (threadsafe)
			return insertFunction(self(), key, value);
		return
			let(slot,
				slotForOrInsertionPoint(key),
				if_(slot == (sword_t)-1,
					//call the library function
					insertFunction(self(), key, value),
					(keys() + slot).store(key) >>
						(values() + slot).store(value)
					)
				);
		}

	TypedNativeExpression<bool> contains(TypedNativeExpression<key_type> e) const
		{
		return slotFor(e) != (sword_t)-1;
		}

private:
	NativeExpression mThis;
};

