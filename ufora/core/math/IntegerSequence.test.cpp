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
#include "IntegerSequence.hppml"

#include "../UnitTest.hpp"
#include "../UnitTestCppml.hpp"
#include "../containers/ImmutableTreeVector.hppml"
#include "../Logging.hpp"

#include "Random.hpp"


namespace {

ImmutableTreeVector<int> range(long k)
	{
	ImmutableTreeVector<int> tr;

	while (k >= 0)
		{
		tr = k + tr;
		k--;
		}

	return tr;
	}

ImmutableTreeVector<int> create(IntegerSequence s)
	{
	ImmutableTreeVector<int> tr;

	for (long k = 0; k < s.size(); k++)
		tr = tr + s.offsetForIndex(k);

	return tr;
	}

ImmutableTreeVector<int> pick(IntegerSequence s, ImmutableTreeVector<int> vals)
	{
	ImmutableTreeVector<int> tr;

	for (long k = 0; k < s.size(); k++)
		tr = tr + vals[s.offsetForIndex(k)];

	return tr;
	}

ImmutableTreeVector<int> intersect(IntegerSequence s, ImmutableTreeVector<int> vals)
	{
	ImmutableTreeVector<int> tr;

	for (long k = 0; k < vals.size(); k++)
		if (s.contains(vals[k]))
			tr = tr + vals[k];

	return tr;
	}

ImmutableTreeVector<int> slice(
					ImmutableTreeVector<int> i,
					IntegerSequence seq
					)
	{
	ImmutableTreeVector<int> tr;

	for (long k = 0; k < seq.size(); k++)
		{
		int index = seq.offsetForIndex(k);
		if (index >= 0 && index < i.size())
			tr = tr + i[index];
		}

	return tr;
	}

ImmutableTreeVector<int> slice(
					ImmutableTreeVector<int> i,
					Nullable<int64_t> s1,
					Nullable<int64_t> s2,
					Nullable<int64_t> s3
					)
	{
	int64_t stride = (s3 ? *s3 : 1);

	lassert(stride != 0);

	ImmutableTreeVector<int> tr;

	if (stride > 0)
		{
		int64_t start = (s1 ? *s1 : 0);

		if (start < 0)
			start = start + i.size();

		int64_t stop = (s2 ? *s2 : i.size());

		if (stop < 0)
			stop += i.size();

		while (start < 0)
			start += stride;

		while (start < stop && start < i.size())
			{
			tr = tr + i[start];
			start += stride;
			}
		}
	else
		{
		int64_t start = (s1 ? *s1 : (int64_t)i.size() - 1);

		if (start < 0)
			start = start + i.size();

		int64_t stop = (s2 ? *s2 : -1 - (int64_t)i.size());

		if (stop < 0)
			stop += i.size();

		while (start >= i.size())
			start += stride;

		while (start > stop && start >= 0)
			{
			tr = tr + i[start];
			start += stride;
			}
		}

	return tr;
	}
}


BOOST_AUTO_TEST_CASE( test_math_IntegerSequence )
	{
	typedef IntegerSequence S;

	BOOST_CHECK_EQUAL_CPPML(S(10), S(10).slice(0));
	BOOST_CHECK_EQUAL_CPPML(S(5), S(10).slice(null(), -5));

	BOOST_CHECK_EQUAL_CPPML(S(3, 2), S(10).slice(2, -5));
	BOOST_CHECK_EQUAL_CPPML(S(3, 2), S(10).slice(-8, -5));

	BOOST_CHECK_EQUAL_CPPML(S(3, 2), S(10).slice(2, 5));
	BOOST_CHECK_EQUAL_CPPML(S(3, 2), S(10).slice(-8, 5));

	BOOST_CHECK_EQUAL_CPPML(S(10, 9, -1), S(10).slice(null(), null(), null() << (int64_t)-1));


	BOOST_CHECK_EQUAL_CPPML(S(10).slice(5,10), S(10).slice(5, 100));
	BOOST_CHECK_EQUAL_CPPML(S(3, 5, 2), S(10).slice(5, 100, 2));

	//the changes "indenting by two" and "reversing order" are commutative
	BOOST_CHECK_EQUAL_CPPML(
		S(10).slice(2,-2).slice(null(),null(),-1),
		S(10).slice(null(),null(),-1).slice(2,-2)
		);

	BOOST_CHECK_EQUAL_CPPML(S(500, 0, 1).slice(S(333,1,3)), S(167,1,3));
	}

BOOST_AUTO_TEST_CASE( test_math_IntegerSequence_Slice )
	{
	IntegerSequence s1(500, 0, 1);

	IntegerSequence s2 = s1.slice(Nullable<int64_t>(1), null(), Nullable<int64_t>(3));

	IntegerSequence s3 = s1.slice(IntegerSequence(500, 1, 3));

	BOOST_CHECK_EQUAL_CPPML(s2, s3);
	}

BOOST_AUTO_TEST_CASE( test_math_IntegerSequence_Random )
	{
	for (long seed = 1; seed < 10000; seed++)
		{
		Ufora::math::Random::Uniform<float> generator(seed);

		IntegerSequence seq(generator() * 20, (generator() - .5) * 20, (generator() - .5) * 8);
		if (seq.stride() == 0)
			seq.stride() = 1;

		ImmutableTreeVector<int> vals = create(seq);

		Nullable<int64_t> s1, s2, s3;

		if (generator() > .25)
			s1 = (generator() - .5) * 5;

		if (generator() > .25)
			s2 = (generator() - .5) * 5;

		if (generator() > .25)
			s3 = (generator() - .5) * 8;

		if (s3 && *s3 == 0)
			s3 = null();

		ImmutableTreeVector<int> slicedVals = slice(vals, s1, s2, s3);

		IntegerSequence slicedSeq = seq.slice(s1, s2, s3);

		ImmutableTreeVector<int> slicedSeqVals = create(slicedSeq);

		lassert_dump(
			slicedSeqVals == slicedVals,
			"Slicing " << prettyPrintString(seq) << " with "
				<< "[" << prettyPrintString(s1) << ", " << prettyPrintString(s2) << ", "
				<< prettyPrintString(s3) << "] produced "
				<< prettyPrintString(slicedSeq) << " = " << prettyPrintString(slicedSeqVals)
				<< " != " << prettyPrintString(slicedVals)
			);
		}
	}

BOOST_AUTO_TEST_CASE( test_math_IntegerSequence_Slice_Random )
	{
	for (long seed = 1; seed < 10000; seed++)
		{
		Ufora::math::Random::Uniform<float> generator(seed);

		IntegerSequence seq(generator() * 20, (generator() - .5) * 20, (generator() - .5) * 8);
		IntegerSequence seq2(generator() * 20, (generator() - .5) * 20, (generator() - .5) * 8);

		if (seq.stride() == 0)
			seq.stride() = 1;

		if (seq2.stride() == 0)
			seq2.stride() = 1;

		ImmutableTreeVector<int> vals = create(seq);

		ImmutableTreeVector<int> slicedVals = slice(vals, seq2);

		IntegerSequence slicedSeq = seq.slice(seq2);

		ImmutableTreeVector<int> slicedSeqVals = create(slicedSeq);

		lassert_dump(
			slicedSeqVals == slicedVals,
			"Slicing " << prettyPrintString(seq) << " with "
				<< prettyPrintString(seq2) << " produced "
				<< prettyPrintString(slicedSeq) << " = " << prettyPrintString(slicedSeqVals)
				<< " != " << prettyPrintString(slicedVals)
			);
		}
	}

BOOST_AUTO_TEST_CASE( test_math_IntegerSequence_Intersection_Random )
	{
	for (long seed = 1; seed < 10000; seed++)
		{
		Ufora::math::Random::Uniform<float> generator(seed);

		IntegerSequence seq(generator() * 50, (generator() - .5) * 50, (generator() - .25) * 10);
		if (seq.stride() == 0)
			seq.stride() = 1;

		IntegerSequence toIntersectWith(generator() * 50, (generator() - .5) * 50, (generator() - .25) * 10);
		if (toIntersectWith.stride() == 0)
			toIntersectWith.stride() = 1;

		ImmutableTreeVector<int> vals = create(seq);

		ImmutableTreeVector<int> intersectedVals = intersect(toIntersectWith, vals);

		IntegerSequence intersectedSeq = seq.intersect(toIntersectWith);

		ImmutableTreeVector<int> intersectedSeqVals = create(intersectedSeq);

		lassert_dump(
			intersectedSeqVals == intersectedVals,
			"Intersecting " << prettyPrintString(seq) << " with "
				<< prettyPrintString(toIntersectWith) << " produced "
				<< prettyPrintString(intersectedSeq) << " = " << prettyPrintString(intersectedSeqVals)
				<< " != " << prettyPrintString(intersectedVals)
			);
		}
	}


