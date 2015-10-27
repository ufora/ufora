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
#include "ForaValueArray.hppml"
#include "ForaValueArrayImpl.hppml"
#include "ForaValueArrayTestFixture.hppml"
#include "ForaValueArraySpaceRequirements.hppml"
#include "../../../core/UnitTest.hpp"
#include "../../../core/math/Random.hpp"
#include "../../../core/threading/CallbackScheduler.hppml"

using TypedFora::Abi::ForaValueArray;
using TypedFora::Abi::ForaValueArrayImpl;
using TypedFora::Abi::PackedForaValues;
using TypedFora::Abi::ForaValueArraySpaceRequirements;

class ForaValueArrayFuzzTest {
public:
	ForaValueArrayFuzzTest(long seed) : 
			mRandom(seed)
		{
		mMemoryPool = MemoryPool::getFreeStorePool();
		}

	~ForaValueArrayFuzzTest()
		{
		for (long k = 0; k < mArrays.size(); k++)
			{
			LOG_DEBUG << "Ripping down " << k;
			mMemoryPool->destroy(mArrays[k]);
			}
		}

	void doSomething()
		{
		performARandomAction();
		}

	void performARandomAction()
		{
		if (mRandom() < .3 || !mValues.size())
			createAVector();
			else
		if (mValues.size() > 2 && mRandom() < .2)
			appendSomeVectorsToAnother();
			else
		if (mRandom() < .1)
			appendSingleValue(
				mRandom() * mValues.size(),
				ImplValContainer(CSTValue((int64_t)(mRandom() * 1000)))
				);
		else
			appendValues(
				mRandom() * mValues.size(),
				randomValues()
				);
		}

	void appendSomeVectorsToAnother()
		{
		long targetIx = mRandom() * mValues.size();

		//half the time, let's do this to the top vector, which is empty
		if (mRandom() < .5)
			{
			createAVector();
			targetIx = mValues.size() - 1;
			}

		std::vector<int> otherIndices;

		for (long k = mRandom() * 4; k >= 0; k--)
			{
			long ix = mRandom() * mValues.size();
			if (ix != targetIx)
				otherIndices.push_back(ix);
			}

		if (mArrays[targetIx]->size() == 0 && mRandom() < .75)
			{
			ForaValueArraySpaceRequirements space = ForaValueArraySpaceRequirements::empty();

			for (int ix: otherIndices)
				space = space + mArrays[ix]->getSpaceRequirements();

			mArrays[targetIx]->prepareForAppending(space);
			}

		LOG_DEBUG << "Appending to " << targetIx << ": " << otherIndices << ". Cur = " << mValues[targetIx];

		for (int ix: otherIndices)
			{
			LOG_DEBUG << "\t" << mValues[ix];
			for (auto v: mValues[ix])
				mValues[targetIx].push_back(v);
			mArrays[targetIx]->append(*mArrays[ix]);
			}
		}

	void createAVector()
		{
		LOG_DEBUG << "Create a vector";

		mValues.push_back(std::vector<ImplValContainer>());
		mArrays.push_back(ForaValueArray::Empty(mMemoryPool));
		}

	void appendSingleValue(long index, ImplValContainer v)
		{
		LOG_DEBUG << "Append " << v.type() << " to " << index;

		mValues[index].push_back(v);
		mArrays[index]->append(v);
		}

	void appendValues(long index, ImmutableTreeVector<ImplValContainer> v)
		{
		LOG_DEBUG << "Append " << v << " to " << index << ": " << mArrays[index];

		ForaValueArrayImpl subArray(mMemoryPool);

		for (auto e: v)
			subArray.append(e);

		if (mRandom() < .5)
			{
			LOG_DEBUG << "\tEntire vector";
			for (auto e: v)
				mValues[index].push_back(e);

			for (long k = 0; k < subArray.size();k++)
				lassert(subArray[k] == v[k]);

			mArrays[index]->append(subArray);
			}
		else
			{
			long low = mRandom() * v.size();
			long high = mRandom() * v.size();

			if (low < high)
				{
				LOG_DEBUG << "\tSliced from " << low << ":" << high;

				for (long k = low; k < high; k++)
					mValues[index].push_back(v[k]);

				mArrays[index]->append(subArray, low, high);
				}
			}
		}

	ImmutableTreeVector<ImplValContainer> randomValues()
		{
		if (mRandom() < .25)
			return randomStrings(1 + mRandom() * 5);

		if (mRandom() < .33)
			return randomIntegers(1 + mRandom() * 5);

		if (mRandom() < .5)
			return randomDoubles(1 + mRandom() * 5);

		return randomTuples(1 + mRandom() * 5, mRandom() > .5);
		}

	ImmutableTreeVector<ImplValContainer> randomStrings(long count)
		{
		ImmutableTreeVector<ImplValContainer> result;

		for (long k = 0; k < count; k++)
			result = result + ImplValContainer(CSTValue(boost::lexical_cast<string>(mRandom())));

		return result;
		}

	ImmutableTreeVector<ImplValContainer> randomIntegers(long count)
		{
		ImmutableTreeVector<ImplValContainer> result;

		for (long k = 0; k < count; k++)
			result = result + ImplValContainer(CSTValue(uint64_t(10000 * mRandom())));

		return result;
		}

	ImmutableTreeVector<ImplValContainer> randomDoubles(long count)
		{
		ImmutableTreeVector<ImplValContainer> result;

		for (long k = 0; k < count; k++)
			result = result + ImplValContainer(CSTValue(uint64_t(10000 * mRandom())));

		return result;
		}

	ImmutableTreeVector<ImplValContainer> randomTuples(long count, bool POD)
		{
		ImmutableTreeVector<ImplValContainer> result;

		for (long k = 0; k < count; k++)
			result = result + randomTuple(POD);

		return result;
		}

	ImplValContainer randomTuple(bool POD)
		{
		ImmutableTreeVector<ImplValContainer> vals;

		for (long k = mRandom() * 5; k >= 0; k--)
			vals = vals + randomValue(POD);

		return vals;
		}

	ImplValContainer randomValue(bool POD)
		{
		if (mRandom() < .25)
			return randomTuple(POD);

		if (!POD && mRandom() < .5)
			return randomStrings(1)[0];

		return randomIntegers(1)[0];
		}

	void validateState()
		{
		lassert(mValues.size() == mArrays.size());

		for (long ix = 0; ix < mValues.size(); ix++)
			{
			lassert(mValues[ix].size() == mArrays[ix]->size());
			for (long k = 0; k < mValues[ix].size();k++)
				lassert_dump(
					mValues[ix][k] == (*mArrays[ix])[k],
					"index " << k << ": " 
						<< prettyPrintString(mValues[ix][k]) << " vs. " 
						<< prettyPrintString((*mArrays[ix])[k])
					);
			}
		}

private:
	MemoryPool* mMemoryPool;

	std::vector<ForaValueArray*> mArrays;

	std::vector<std::vector<ImplValContainer> > mValues;

	Ufora::math::Random::Uniform<float> mRandom;
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_ForaValueArrayFuzzer, ForaValueArrayTestFixture )

BOOST_AUTO_TEST_CASE ( test_fuzz_fora_value_array )
	{
	for (long seed = 1; seed < 1000; seed++)
		{
		LOG_DEBUG << "Seed: " << seed;
		ForaValueArrayFuzzTest test(seed);

		for (long passes = 0; passes < 30; passes++)
			test.doSomething();

		test.validateState();
		}
	}

BOOST_AUTO_TEST_SUITE_END( )

