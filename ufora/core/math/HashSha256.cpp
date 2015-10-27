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
#include "HashSha256.hpp"
#include "../cppml/CPPMLPrettyPrinter.hppml"
#include <openssl/sha.h>
#include "Hash.hpp"

namespace Ufora {
namespace math {
namespace crypto {

HashSha256 HashSha256::Sha256(const void* data, uint32_t sz)
	{
	HashSha256 tr;

	if (sz)
		::SHA256((const unsigned char*)data, sz, (unsigned char*)&tr);
	
	return tr;
	}
HashSha256 operator+(const HashSha256& l, const HashSha256& r)
	{
	char data[sizeof(HashSha256) * 2];
	((HashSha256*)data)[0] = l;
	((HashSha256*)data)[1] = r;

	HashSha256 tr = HashSha256::Sha256(data, sizeof(HashSha256)*2);

	return tr;
	}

std::string hashToString(const HashSha256& in)
	{
	return bytesToHexString((unsigned char*)&in, sizeof(in));
	}

}
}
}
