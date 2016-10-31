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

#include <boost/random.hpp>
#include "../lassert.hpp"

namespace Ufora {
namespace math {
namespace Random {

template<class scalar_type>
class Normal {
public:
		Normal(uint32_t inSeed = 1u) :
				mSampler(mGen, mNormal)
			{
			mGen.seed(boost::uint32_t(inSeed));
			}

		scalar_type	operator()(void)
			{
			return mSampler();
			}

		template<class T>
		T operator()(T value)
			{
			return mSampler(value);
			}

		typedef typename boost::variate_generator<boost::mt19937&, boost::normal_distribution<scalar_type> >::result_type result_type;

		result_type min() const
			{
			return mSampler.min();
			}

		result_type max() const
			{
			return mSampler.max();
			}
private:
		boost::normal_distribution<scalar_type> mNormal;

		boost::mt19937 mGen;

	    boost::variate_generator<boost::mt19937&, boost::normal_distribution<scalar_type> > mSampler;
};

template<class scalar_type,
	bool = std::is_integral<scalar_type>::value,
	bool = std::is_floating_point<scalar_type>::value>
class Uniform;

template<class scalar_type>
class Uniform<scalar_type, false, true> {
public:
		Uniform(uint32_t inSeed = 1u) :
				mSampler(mGen, mUniform)
			{
			mGen.seed(boost::uint32_t(inSeed));
			}

		scalar_type	operator()(void)
			{
			return mSampler();
			}

		template<class T>
		scalar_type operator()(T value)
			{
			return mSampler(value);
			}

		typedef typename boost::variate_generator<boost::mt19937&, boost::uniform_real<scalar_type> >::result_type result_type;

		result_type min()
			{
			return mSampler.min();
			}

		result_type max()
			{
			return mSampler.max();
			}
private:
		boost::uniform_real<scalar_type> mUniform;

		boost::mt19937 mGen;

		boost::variate_generator<boost::mt19937&, boost::uniform_real<scalar_type> > mSampler;
};

template<class scalar_type>
class Uniform<scalar_type, true, false> {
public:
		Uniform(uint32_t inSeed = 1u) :
				mSampler(mGen, mUniform)
			{
			mGen.seed(boost::uint32_t(inSeed));
			}

		scalar_type	operator()(void)
			{
			return mSampler();
			}

		template<class T>
		scalar_type operator()(T value)
			{
			return mSampler(value);
			}

		typedef typename boost::variate_generator<boost::mt19937&, boost::uniform_int<scalar_type> >::result_type result_type;

		result_type min()
			{
			return mSampler.min();
			}

		result_type max()
			{
			return mSampler.max();
			}
private:
		boost::uniform_int<scalar_type> mUniform;

		boost::mt19937 mGen;

	    boost::variate_generator<boost::mt19937&, boost::uniform_int<scalar_type> > mSampler;
};

template<class T, class scalar_type>
decltype(*T().begin()) pickRandomlyFromSet(
								const T& values,
								Uniform<scalar_type>& random
								)
	{
	int which = values.size();

	while (which >= values.size())
		which = random() * values.size();

	auto it = values.begin();

	while (which)
		{
		it++;
		which--;
		}

	return *it;
	}

template<class T, class scalar_type, class weight_function_type>
decltype(*T().begin()) pickRandomlyFromSetWithWeight(
								const T& values,
								Uniform<scalar_type>& random,
								weight_function_type weightFunction
								)
	{
	double totalWeight = 0;

	for (auto val: values)
		totalWeight += weightFunction(val);

	lassert(totalWeight > 0.0);

	double w = totalWeight * random();

	for (auto val: values)
		if (weightFunction(val) >= w)
			return val;
		else
			w -= weightFunction(val);

	lassert(false);
	}


}; //namespace Random
}; //namespace math
}; //namespace Ufora

