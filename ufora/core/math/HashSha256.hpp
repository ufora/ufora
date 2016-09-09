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

using namespace std;

namespace Ufora {
namespace math {
namespace crypto {

class HashSha256 {
public:
		const static int wordCount = 8;

		HashSha256()
			{
			for (int32_t k = 0; k < wordCount;k++)
				mData[k] = k;
			}
		HashSha256(uint32_t t)
			{
			for (int32_t k = 0; k < wordCount;k++)
				mData[k] = 0;
			mData[0] = t;
			}
		HashSha256(uint32_t t, uint32_t t2)
			{
			for (int32_t k = 0; k < wordCount;k++)
				mData[k] = 0;
			mData[0] = t;
			mData[1] = t2;
			}
		HashSha256(uint32_t t, uint32_t t2, uint32_t t3)
			{
			for (int32_t k = 0; k < wordCount;k++)
				mData[k] = 0;
			mData[0] = t;
			mData[1] = t2;
			mData[2] = t3;
			}
		HashSha256(uint32_t t, uint32_t t2, uint32_t t3, uint32_t t4)
			{
			for (int32_t k = 0; k < wordCount;k++)
				mData[k] = 0;
			mData[0] = t;
			mData[1] = t2;
			mData[2] = t3;
			mData[3] = t4;
			}
		HashSha256(const HashSha256& in)
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
		bool operator==(const HashSha256& in) const
			{
			return cmp(in) == 0;
			}
		bool operator!=(const HashSha256& in) const
			{
			return cmp(in) != 0;
			}
		bool operator<(const HashSha256& in) const
			{
			return cmp(in) == -1;
			}
		bool operator>(const HashSha256& in) const
			{
			return cmp(in) == 1;
			}
		int32_t cmp(const HashSha256& in) const
			{
			for (int32_t k = 0; k < wordCount;k ++)
				if (mData[k] < in.mData[k])
					return -1;
					else
				if (mData[k] > in.mData[k])
					return 1;
			return 0;
			}
		inline static HashSha256 Sha256(std::string s)
			{
			return Sha256(s.c_str(), s.size());
			}
		static HashSha256 Sha256(const void* data, uint32_t sz);
private:
		uint32_t mData[wordCount];
};

template<class T>
HashSha256 HashSha256Raw(const T& in)
	{
	return HashSha256::Sha256(&in, sizeof(in));
	}

HashSha256 operator+(const HashSha256& l, const HashSha256& r);

std::string hashToString(const HashSha256& in);

}
}
}
