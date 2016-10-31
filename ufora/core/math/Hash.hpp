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
#include <vector>
#include <map>
#include <set>
#include "../serialization/Serialization.hpp"
#include "Nullable.hpp"
#include <boost/functional/hash.hpp>
#include <boost/python.hpp>

using namespace std;

class Hash {
public:
		Hash()
			{
			for (int32_t k = 0; k < 5;k++)
				mData[k] = k;
			}
		Hash(uint32_t t)
			{
			for (int32_t k = 0; k < 5;k++)
				mData[k] = 0;
			mData[0] = t;
			}
		Hash(uint32_t t, uint32_t t2)
			{
			for (int32_t k = 0; k < 5;k++)
				mData[k] = 0;
			mData[0] = t;
			mData[1] = t2;
			}
		Hash(uint32_t t, uint32_t t2, uint32_t t3)
			{
			for (int32_t k = 0; k < 5;k++)
				mData[k] = 0;
			mData[0] = t;
			mData[1] = t2;
			mData[2] = t3;
			}
		Hash(uint32_t t, uint32_t t2, uint32_t t3, uint32_t t4)
			{
			for (int32_t k = 0; k < 5;k++)
				mData[k] = 0;
			mData[0] = t;
			mData[1] = t2;
			mData[2] = t3;
			mData[3] = t4;
			}
		Hash(uint8_t* data, size_t bytes)
			{
			lassert(bytes > 0);
			lassert(bytes <= 20);

			memcpy((uint8_t*)mData, data, bytes);
			memset((uint8_t*)mData + bytes, 0, 20 - bytes);
			}
		Hash(const Hash& in)
			{
			*this = in;
			}
		uint32_t& operator[](int32_t ix)
			{
			return mData[ix];
			}
		const uint32_t& operator[](int32_t ix) const
			{
			return mData[ix];
			}
		bool operator==(const Hash& in) const
			{
			return cmp(in) == 0;
			}
		bool operator!=(const Hash& in) const
			{
			return cmp(in) != 0;
			}
		bool operator<(const Hash& in) const
			{
			return cmp(in) == -1;
			}
		bool operator<=(const Hash& in) const
			{
			return cmp(in) <= 0;
			}
		bool operator>(const Hash& in) const
			{
			return cmp(in) == 1;
			}
		bool operator>=(const Hash& in) const
			{
			return cmp(in) >= 0;
			}

		int32_t cmp(const Hash& in) const
			{
			for (int32_t k = 0; k < 5;k ++)
				if (mData[k] < in.mData[k])
					return -1;
					else
				if (mData[k] > in.mData[k])
					return 1;
			return 0;
			}

		inline static Hash SHA1(std::string s)
			{
			return SHA1(s.c_str(), s.size());
			}

		static Hash SHA1(const void* data, uint32_t sz);

		inline static Hash CityHash(std::string s)
			{
			return CityHash(s.c_str(), s.size());
			}

		static Hash CityHash(const void* data, uint32_t sz);

		static Hash SHA1Strided(
			const void* data,
			uint32_t inBlockSize,
			uint32_t inBlockStride,
			uint32_t inCount
			);

		static Hash SHA1Scattered(
			const void** data,
			uint32_t inBlockSize,
			uint32_t inBlockNudge,
			uint32_t inCount
			);

private:
		uint32_t mData[5];
};

template<class T>
Hash hashRaw(const T& in)
	{
	return Hash::SHA1(&in, sizeof(in));
	}

Hash operator+(const Hash& l, const Hash& r);
Hash operator^(const Hash& l, const Hash& r);

std::string bytesToHexString(unsigned char* data, uint32_t bytes);
std::string hashToString(const Hash& in);
Hash stringToHash(const std::string& in);

def_binary_serializer( Hash );

template<class T>
class CPPMLPrettyPrint;

class CPPMLPrettyPrintStream;

template<>
class CPPMLPrettyPrint<Hash > {
public:
		static void prettyPrint(CPPMLPrettyPrintStream& s, const Hash& t);
};

template<class T, class kind>
class CPPMLEquality;

template<>
class CPPMLEquality<Hash, void> {
public:
		static char cmp(const Hash& lhs, const Hash& rhs)
			{
			return lhs.cmp(rhs);
			}
};
template<class T, class T2>
class CPPMLTransform;

template<>
class CPPMLTransform<Hash, void> {
public:
		template<class F>
		static Nullable<Hash > apply(const Hash& in, const F& f)
			{
			return null();
			}
};
template<class T, class T2>
class CPPMLTransformWithIndex;

template<>
class CPPMLTransformWithIndex<Hash, void> {
public:
		template<class F, class F2>
		static Nullable<Hash > apply(const Hash& in, const F& f, const F2& f2)
			{
			return null();
			}
};

template<class T, class T2>
class CPPMLVisit;

template<>
class CPPMLVisit<Hash, void> {
public:
		template<class F>
		static void apply(const Hash& in, const F& f)
			{
			}
};
template<class T, class T2>
class CPPMLVisitWithIndex;

template<>
class CPPMLVisitWithIndex<Hash, void> {
public:
		template<class F, class F2>
		static void apply(const Hash& in, const F& f, const F2& inF2)
			{
			}
};

class OHashProtocol : public OProtocol {
public:
		OHashProtocol(Hash& outHash);
		~OHashProtocol();

		void write(uword_t inByteCount, void *inData);
		uword_t position(void);
private:
		uword_t 	mPosition;
		void*		mData;
		Hash&		mOutHash;
};


class HashingStreamSerializer {
public:
		HashingStreamSerializer(Hash& outHash) : mProtocol(outHash) {}

		void writeBytes(const void* data, uword_t sz)
			{
			mProtocol.write(sz, (void*)data);
			}
		template<class T>
		void serialize(const T& in)
			{
			Serializer<T, HashingStreamSerializer>::serialize(*this, in);
			}
private:
		OHashProtocol mProtocol;
};

//does one level of hashing itself, then passes back to HSS.
class HashingStreamSerializerDirect {
public:
		HashingStreamSerializerDirect(HashingStreamSerializer& d) : m(d)
			{
			}
		void writeBytes(const void* data, uword_t sz)
			{
			m.writeBytes(data, sz);
			}
		template<class T>
		void serialize(const T& in)
			{
			m.serialize(in);
			}
private:
		HashingStreamSerializer& m;
};

template<class T>
inline Hash hashValue(const T& in)
	{
	Hash tr;
		{
		HashingStreamSerializer s(tr);

		Serializer<T, HashingStreamSerializer>::serialize(s, in);
		}

	return tr;
	}

template<class T>
inline Hash hashCPPMLDirect(const T& in)
	{
	Hash tr;

		{
		HashingStreamSerializer s(tr);

		HashingStreamSerializerDirect s2(s);
		Serializer<T, HashingStreamSerializerDirect>::serialize(s2, in);
		}

	return tr;
	}

#define macro_defineMemberHashFunction(T)	\
template<>\
class Serializer<T, HashingStreamSerializer> {\
public:\
		static inline void serialize(HashingStreamSerializer& s, const T& in)\
			{\
			s.serialize(in.hash());\
			}\
};\


#define macro_defineMemberHashFunctionForward(T)	\
template<>\
class Serializer<T, HashingStreamSerializer> {\
public:\
		static void serialize(HashingStreamSerializer& s, const T& in);\
};\



#define macro_defineMemberHashFunctionBody(T)	\
void Serializer<T, HashingStreamSerializer>::serialize(HashingStreamSerializer& s, const T& in)\
	{\
	s.serialize(in.hash());\
	};\



typedef Hash hash_type;

namespace boost {
template<>
class hash<Hash> : public std::unary_function<Hash, std::size_t> {
public:
		std::size_t operator()(Hash const& in) const
			{
			return reinterpret_cast<const std::size_t*>(&in)[0];
			}
};

};

template<>
class Serializer<boost::python::object, HashingStreamSerializer> {
public:
		static inline void serialize(HashingStreamSerializer& s, const boost::python::object& in)
			{
			s.serialize((size_t)in.ptr());
			}
};

