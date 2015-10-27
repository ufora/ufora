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
#include "Hash.hpp"
#include "../cppml/CPPMLPrettyPrinter.hppml"
#include "../../third_party/cityhash/city.hpp"
#include <openssl/sha.h>

Hash Hash::SHA1(const void* data, uint32_t sz)
	{
	Hash tr;

	if (sz)
		::SHA1((const unsigned char*)data, sz, (unsigned char*)&tr);
	
	return tr;
	}

Hash Hash::SHA1Strided(
			const void* data, 
			uint32_t inBlockSize, 
			uint32_t inBlockStride, 
			uint32_t inCount
			)
	{
	if (inBlockStride == inBlockStride)
		return SHA1(data, inBlockSize * inCount);
	
	SHA_CTX ctx;

	SHA1_Init(&ctx);

	uint8_t* dataAsInt = (uint8_t*) data;

	for (long k = 0; k < inCount;k++)
		SHA1_Update(&ctx, dataAsInt + inBlockStride * k, inBlockSize);

	hash_type tr;

	SHA1_Final((unsigned char*)&tr, &ctx);

	return tr;
	}

Hash operator+(const Hash& l, const Hash& r)
	{
	char data[sizeof(Hash) * 2];
	((Hash*)data)[0] = l;
	((Hash*)data)[1] = r;

	Hash tr = Hash::CityHash(data, sizeof(Hash)*2);

	return tr;
	}

Hash operator^(const Hash& l, const Hash& r)
	{
	char data[sizeof(Hash) * 2];
	((Hash*)data)[0] = l;
	((Hash*)data)[1] = r;
	for (int i = 0; i < sizeof(Hash); ++i)
		data[i] ^= data[sizeof(Hash) + i];
	return ((Hash*)data)[0];
	}

std::string bytesToHexString(unsigned char* data, uint32_t bytes)
	{
	std::string s;
	s.resize(bytes * 2);

	char hex[] = { '0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F'};
	for (int32_t k = 0; k < bytes; k++)
		{
		s[k * 2] = hex[data[k] >> 4];
		s[k * 2 + 1] = hex[data[k] & 0xF];
		}

	return s;
	}

unsigned char hexCharValue(unsigned char val)
	{
	if (val >= '0' && val <= '9')
		return val - '0';
	if (val >= 'a' && val <= 'f')
		return val - 'a' + 10;
	if (val >= 'A' && val <= 'F')
		return val - 'A' + 10;
	lassert(false);
	}

void hexStringToBytes(unsigned char* srcData, unsigned char* destData, uint32_t hexDigits)
	{
	lassert(hexDigits % 2 == 0);

	for (long k = 0; k < hexDigits;k += 2)
		destData[k/2] = hexCharValue(srcData[k]) * 16 + hexCharValue(srcData[k+1]);
	}

std::string hashToString(const Hash& in)
	{
	return bytesToHexString((unsigned char*)&in, sizeof(in));
	}

Hash stringToHash(const std::string& in)
	{
	lassert(in.size() == sizeof(Hash) * 2);

	Hash tr;

	hexStringToBytes((unsigned char*)in.c_str(), (unsigned char*)&tr, in.size());

	return tr;
	}

OHashProtocol::OHashProtocol(Hash& outHash) :
		mOutHash(outHash),
		mPosition(0),
		mData(new SHA_CTX)
	{
	SHA1_Init((SHA_CTX*)mData);
	}

OHashProtocol::~OHashProtocol()
	{
	SHA1_Final((unsigned char*)&mOutHash, (SHA_CTX*)mData);
	delete (SHA_CTX*)mData;
	}

void OHashProtocol::write(uword_t inByteCount, void *inData)
	{
	//by default, we ignore the endianness
	
	SHA1_Update((SHA_CTX*)mData, inData, inByteCount);

	mPosition += inByteCount;
	}
uword_t OHashProtocol::position(void)
	{
	return mPosition;
	}

void CPPMLPrettyPrint<Hash>::prettyPrint(CPPMLPrettyPrintStream& s, const Hash& t)
	{
	s << hashToString(t).substr(0, 12) + "...";
	}

Hash Hash::CityHash(const void* data, uint32_t sz)
	{
	hash_type newHash;

	//use a different seed on the first 4 bytes than on the last byte
	uint128 someSeed(503,127);

	((uint128*)&newHash)[0] = CityHash128WithSeed((const char*)data, sz, someSeed);

	newHash[4] = CityHash32((const char*)data, sz);

	return newHash;
	}

