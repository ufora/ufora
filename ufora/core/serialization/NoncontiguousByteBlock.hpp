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

#include <vector>
#include <string>
#include "../Common.hppml"
#include "../PolymorphicSharedPtr.hpp"
#include "../cppml/CPPMLPrettyPrinter.hppml"
#include "../math/Nullable.hpp"
#include "../math/Hash.hpp"


//serialized blocks of data held in non-contiguous memory
class NoncontiguousByteBlock : public PolymorphicSharedPtrBase<NoncontiguousByteBlock> {
public:
	NoncontiguousByteBlock();

	explicit NoncontiguousByteBlock(std::string&& inString);

	void push_back(std::string&& inString);

	uint32_t totalByteCount(void) const;

	uint32_t size(void) const;

	std::string& operator[](uint32_t inIndex);

	const std::string& operator[](uint32_t inIndex) const;

	std::string toString(void) const;

	void clear(void);

	hash_type hash() const;
private:
	std::vector<std::string> mStrings;	

	mutable Nullable<hash_type> mHash;

	uint32_t mTotalBytes;
};

template<class T1, class T2>
class Serializer;

template<class T1, class T2>
class Deserializer;

template<class storage_type>
class Serializer<NoncontiguousByteBlock, storage_type> {
public:
		static void serialize(storage_type& s, const NoncontiguousByteBlock& t)
			{
			s.serialize((uint32_t)t.size());
			for (uint32_t k = 0; k < t.size();k++)
				s.serialize(t[k]);
			}
};

template<class storage_type>
class Deserializer<NoncontiguousByteBlock, storage_type> {
public:
		static void deserialize(storage_type& s, NoncontiguousByteBlock& t)
			{
			t.clear();
			
			uint32_t sz;
			s.deserialize(sz);
			
			while (sz > 0)
				{
				std::string aString;
				
				s.deserialize(aString);
				
				t.push_back(std::move(aString));

				sz--;
				}
			}
};

template<class storage_type>
class Serializer<PolymorphicSharedPtr<NoncontiguousByteBlock>, storage_type> {
public:
		static void serialize(storage_type& s, const PolymorphicSharedPtr<NoncontiguousByteBlock>& t)
			{
			if (t)
				{
				s.serialize((bool)true);
				s.serialize(*t);
				}
			else
				s.serialize((bool)false);
			}
};

template<class storage_type>
class Deserializer<PolymorphicSharedPtr<NoncontiguousByteBlock>, storage_type> {
public:
		static void deserialize(storage_type& s, PolymorphicSharedPtr<NoncontiguousByteBlock>& t)
			{
			t.reset();

			bool has;
			s.deserialize(has);

			if (!has)
				return;

			t.reset(new NoncontiguousByteBlock());
			s.deserialize(*t);
			}
};

template<>
class CPPMLPrettyPrint<PolymorphicSharedPtr<NoncontiguousByteBlock> > {
public:
		static void prettyPrint(CPPMLPrettyPrintStream& s, const PolymorphicSharedPtr<NoncontiguousByteBlock>& t)
			{
			if (t)
				streamTo(s, "NoncontiguousByteBlock(" + prettyPrintString(t->totalByteCount()) + ")");
			else
				streamTo(s, "NoncontiguousByteBlock(<empty>)");
			}
};


template<class T, class T2>
class CPPMLTransform;

template<>
class CPPMLTransform<PolymorphicSharedPtr<NoncontiguousByteBlock>, void> {
public:
		template<class F>
		static Nullable<PolymorphicSharedPtr<NoncontiguousByteBlock> > apply(
							const PolymorphicSharedPtr<NoncontiguousByteBlock>& in, 
							const F& f
							)
			{
			return null();
			}
};


template<>
class CPPMLEquality<PolymorphicSharedPtr<NoncontiguousByteBlock>, void> {
public:
		static char cmp(	const PolymorphicSharedPtr<NoncontiguousByteBlock>& lhs,
							const PolymorphicSharedPtr<NoncontiguousByteBlock>& rhs
							)
			{
			if (!lhs && !rhs)
				return 0;
			if (lhs && !rhs)
				return 1;
			if (!lhs && rhs)
				return -1;

			return cppmlCmp(lhs->hash(), rhs->hash());
			}
};



class HashingStreamSerializer;

template<>
class Serializer<NoncontiguousByteBlock, HashingStreamSerializer> {
public:
		static void serialize(HashingStreamSerializer& s, const NoncontiguousByteBlock& in);
};

template<>
class Serializer<PolymorphicSharedPtr<NoncontiguousByteBlock>, HashingStreamSerializer> {
public:
		static void serialize(HashingStreamSerializer& s, const PolymorphicSharedPtr<NoncontiguousByteBlock>& in);
};





