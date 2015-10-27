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
#include "RandomHashGenerator.hpp"
#include <boost/uuid/uuid_generators.hpp>

namespace {

hash_type baseHash = Hash::SHA1("RandomHashGeneratorPrivateSalt");

}

RandomHashGenerator::RandomHashGenerator()
	{
	mHash = Hash::SHA1(
		boost::to_string(boost::uuids::random_generator()())
		);
	}

RandomHashGenerator::RandomHashGenerator(hash_type seed) :
		mHash(seed + baseHash)
	{
	}

hash_type RandomHashGenerator::generateRandomHash()
	{
	boost::mutex::scoped_lock lock(mMutex);
	mHash = mHash + baseHash;
	return mHash;
	}

RandomHashGenerator& RandomHashGenerator::singleton()
	{
	static RandomHashGenerator gen;
	return gen;
	}



