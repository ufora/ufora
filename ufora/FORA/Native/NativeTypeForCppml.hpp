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

#include "NativeTypeFor.hpp"
#include "../../core/lassert.hpp"

template<class T, class meta>
class NativeTypeForCppmlTupleImpl {
public:
};

template<class T, class member_type_in, class accessor_in, const int32_t ix, class TailChain>
class NativeTypeForCppmlTupleImpl<
		T, 
		::CPPML::Chain<
			::CPPML::TupleMember<T, member_type_in, accessor_in, ix>, 
			TailChain
			> 
		> {
public:
	static ImmutableTreeVector<pair<NativeType, uword_t> > get()
		{
		T* tPointer = (T*)0;

		return 
			make_pair(
				NativeType::Composite(
					accessor_in::name(),
					NativeTypeForImpl<member_type_in>::get()
					),
				(uint8_t*)&accessor_in::get(*tPointer) - (uint8_t*)tPointer
				) + 
			NativeTypeForCppmlTupleImpl<T, TailChain>::get()
			;
		}
};

template<class T>
class NativeTypeForCppmlTupleImpl<T, ::CPPML::Null> {
public:
	static ImmutableTreeVector<pair<NativeType, uword_t> > get()
		{
		return emptyTreeVec();
		}
};


template<class T>
NativeType nativeTypeForCppmlTuple()
	{
	//get a list of types and offsets into the tuple
	ImmutableTreeVector<pair<NativeType, uword_t> > offsets = 
		NativeTypeForCppmlTupleImpl<T, typename T::metadata>::get();

	NativeType resultType = NativeType::Composite();

	//build up the tuple type one field at a time
	for (long k = 0; k < offsets.size();k++)
		{
		if (offsets[k].second == resultType.packedSize())
			resultType = resultType + offsets[k].first;
			else
		if (offsets[k].second < resultType.packedSize())
			{
			//the sizes should have been linearly increasing
			lassert_dump(false, "inconsistent typing found: " + prettyPrintString(offsets));
			}
		else
			{
			//add enough padding to compensate for the extra bytes that C++ places in between
			//members to get alignment
			resultType = resultType + 
				NativeType::Composite(
					NativeType::Array(
						NativeType::Integer(8,false),
						offsets[k].second - resultType.packedSize()
						)
					);

			resultType = resultType + offsets[k].first;
			}
		}

	lassert(resultType.packedSize() <= sizeof(T));

	if (resultType.packedSize() < sizeof(T))
		resultType = resultType + 
			NativeType::Composite(
				NativeType::Array(
					NativeType::Integer(8,false),
					sizeof(T) - resultType.packedSize()
					)
				);

	return resultType;
	}


