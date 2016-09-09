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
#include "KeyRangeSet.hppml"

#include "../../core/UnitTest.hpp"


using Ufora::Json;

namespace {

using namespace SharedState;

Keyspace createTestKeyspace(std::string name)
	{
	return Keyspace("TakeHighestIdKeyType", Json::String(name), 1);
	}


std::pair<Nullable<KeyBound>, bool> stringLimit(std::string str, bool isLeftBound)
	{
	return make_pair(Nullable<KeyBound>(KeyBound(Json::String(str), isLeftBound)), false);
	}

std::pair<Nullable<KeyBound>, bool> negativeInfinity()
	{
	return make_pair(null(), true);
	}

std::pair<Nullable<KeyBound>, bool> positiveInfinity()
	{
	return make_pair(null(), false);
	}


namespace SharedState {

void verifyKeybounds(
		std::string leftString,
		bool leftIsLeft,
		std::string rightString,
		bool rightIsLeft,

		// the predicted values of == and <
		bool eq,
		bool lt)
	{
	KeyBound left(Json::String(leftString), leftIsLeft);
	KeyBound right(Json::String(rightString), rightIsLeft);

	bool ne = !eq;
	bool lte = eq || lt;
	bool gt = !lte;
	bool gte = eq || gt;

	lassert((left == right) == eq);
	lassert((left != right) == ne);
	lassert((left < right) == lt);
	lassert((left > right) == gt);
	lassert((left >= right) == gte);
	lassert((left <= right) == lte);
	}


void verifyKeyLimits(
		// passing in args as pairs so we can use descriptive helper funcitons to create them
		const std::pair<Nullable<KeyBound>, bool> leftBoundAndWhichInfinityIfNull,
		const std::pair<Nullable<KeyBound>, bool> rightBoundAndWhichInfinityIfNull,
		bool eq,
		bool lt)
	{

	// In this funciton and boundLT and boundEQ, firstIsLeft and secondIsLeft or here...
	// firstIsNegativeInfinityIfNull or secondIsNegativeInfinityIfNull is a boolean that
	// denotes whether this bound refers to negative or positive infinity if and only if it is null.
	//
	Nullable<KeyBound> left = leftBoundAndWhichInfinityIfNull.first;
	bool leftIsNegativeInfinityIfNull = leftBoundAndWhichInfinityIfNull.second;

	Nullable<KeyBound> right = rightBoundAndWhichInfinityIfNull.first;
	bool rightIsNegativeInfinityIfNull = rightBoundAndWhichInfinityIfNull.second;


	//cout << "testing "
		//<< prettyPrintString(left) << " "  << prettyPrintString(leftIsNegativeInfinityIfNull) << " and "
		//<< prettyPrintString(right) << " " <<  prettyPrintString(leftIsNegativeInfinityIfNull) << endl;

	lassert(
			boundLT(
				left,
				leftIsNegativeInfinityIfNull,
				right,
				rightIsNegativeInfinityIfNull
				) == lt);
	lassert(
			boundEQ(
				left,
				leftIsNegativeInfinityIfNull,
				right,
				rightIsNegativeInfinityIfNull
				) == eq);
	}



BOOST_AUTO_TEST_CASE( test_keybounds )
	{
	// both bounds are left bounds
	verifyKeybounds("abcd", true, "abcd", true,     true, false);
	verifyKeybounds("abc", true, "abcd", true, 		false, true);
	verifyKeybounds("abcde", true, "abcd", true, 	false, false);

	// both are right bounds
	verifyKeybounds("abcd", false, "abcd", false,   true, false);
	verifyKeybounds("abc", false, "abcd", false, 	false, true);
	verifyKeybounds("abcde", false, "abcd", false, 	false, false);

	// first keybound is left and second keybound is right
	verifyKeybounds("abcd", true, "abcd", false,   	false, true);
	verifyKeybounds("abc", true, "abcd", false, 	false, true);
	verifyKeybounds("abcde", true, "abcd", false, 	false, false);

	// both are right bounds
	verifyKeybounds("abcd", false, "abcd", true,   	false, false);
	verifyKeybounds("abc", false, "abcd", true, 	false, true);
	verifyKeybounds("abcde", false, "abcd", true, 	false, false);
	}

BOOST_AUTO_TEST_CASE( test_key_limits )
{
	verifyKeyLimits(
			stringLimit("abdc", true),
			stringLimit("abdc", true),
			true,
			false);

	verifyKeyLimits(
			negativeInfinity(),
			stringLimit("abcd", true),
			false,
			true);

	verifyKeyLimits(
			positiveInfinity(),
			stringLimit("abcd", true),
			false,
			false);

	verifyKeyLimits(
			stringLimit("abcd", true),
			positiveInfinity(),
			false,
			true);

	verifyKeyLimits(
			stringLimit("abcd", true),
			negativeInfinity(),
			false,
			false);

	verifyKeyLimits(
			positiveInfinity(),
			positiveInfinity(),
			true,
			false);

	verifyKeyLimits(
			positiveInfinity(),
			negativeInfinity(),
			false,
			false);

	verifyKeyLimits(
			negativeInfinity(),
			positiveInfinity(),
			false,
			true);

	verifyKeyLimits(
			negativeInfinity(),
			negativeInfinity(),
			true,
			false);

}



std::string nextGreatest(std::string in)
	{
	if (in.size() == 0)
		return "\1";
	if (in[in.size() -1] == 255)
		return in + "\1";
	in[in.size() - 1] = in[in.size() - 1] + 1;
	return in;
	}

const Key produceKeyInRange(const KeyRange& range)
	{

	std::string keyString = nextGreatest("");

	if (range.left())
		keyString = nextGreatest(range.left()->value().getString().value());

	vector<Json> keyName;
	for (int i = 0; i < range.keyspace().dimension(); i++)
		keyName.push_back(Json::String(keyString));

	return Key(range.keyspace(), keyName);

	}


KeyRange createDefaultKeyrange(
		std::pair<Nullable<KeyBound>, bool> leftBound,
		std::pair<Nullable<KeyBound>, bool> rightBound)
	{
	Keyspace testSpace(createTestKeyspace("test"));
	return KeyRange(testSpace, 0, leftBound.first, rightBound.first);
	}

void singleKeyRangeTests(KeyRangeSet s, KeyRange range)
	{
	lassert(s.intersects(range));
	lassert(s.containsKeyspace(range.keyspace()));
	lassert(s.intersection(range).size());
	lassert(*(s.intersection(range).begin()) == range);
	lassert(s.intersects(*(s.intersection(range).begin())));
	lassert(s.containsKey(produceKeyInRange(range)));
	}

void verifySingleKeyrange(
		std::pair<Nullable<KeyBound>, bool> leftBound,
		std::pair<Nullable<KeyBound>, bool> rightBound)
	{
	if (!leftBound.first)
		lassert(leftBound.second == true);
	if (!rightBound.first)
		lassert(rightBound.second == false);

	KeyRange range(createDefaultKeyrange(leftBound, rightBound));
	KeyRangeSet s;

	s.insert(range);
	singleKeyRangeTests(s, range);
	s.erase(range);
	lassert(!s.intersects(range));
	lassert(!s.containsKeyspace(range.keyspace()));
	lassert(!s.intersection(range).size());
	}



 //KeyRanges that intersect in the middle
void verifyIntersectingKeyranges(
		const KeyRange leftRange,
		const KeyRange rightRange,
		const KeyRange result,
		bool adjacent = false)
	{
	KeyRangeSet s;
	s.insert(leftRange);
	bool threw = adjacent;
	// should not be able to insert intersecting keyranges
	// user should instead take the difference and insert it
	try
		{
		s.insert(rightRange);
		}
	catch (std::logic_error e)
		{
		threw = true;
		}
	lassert(threw);
	if (!adjacent)
		{
		set<KeyRange> diff = s.difference(rightRange);
		lassert(diff.size() == 1);
		s.insert(*diff.begin());
		}
	lassert(s.size() == 1);

	// ensure both ranges exhibit all of the expected behavior.
	singleKeyRangeTests(KeyRangeSet(s), leftRange);
	singleKeyRangeTests(KeyRangeSet(s), rightRange);
	set<KeyRange> combined = s.intersection(createDefaultKeyrange(negativeInfinity(), positiveInfinity()));
	lassert(combined.size() == 1);
	lassert(*combined.begin() == result);

	}



BOOST_AUTO_TEST_SUITE(KeyRangeSet_tests)

BOOST_AUTO_TEST_CASE( empty )
{
	KeyRangeSet s;
	const KeyRangeSet& cs = s;
    lassert(s.begin() == s.end());
    lassert(cs.begin() == cs.end());
	KeyRange r;
	lassert(s.lower_bound(r) == s.end());
	lassert(s.upper_bound(r) == s.end());
	lassert(cs.lower_bound(r) == cs.end());
	lassert(cs.upper_bound(r) == cs.end());
	lassert(s.find(r) == s.end());
	lassert(s.size() == 0);
}



BOOST_AUTO_TEST_CASE( test_single_keyrange )
{
	verifySingleKeyrange(negativeInfinity(), positiveInfinity());
	verifySingleKeyrange(stringLimit("aaaaa", true), stringLimit("bbbbb", true));
	verifySingleKeyrange(negativeInfinity(),  stringLimit("bbbbb", true));
	verifySingleKeyrange(stringLimit("bbbbb", true), positiveInfinity());
}

BOOST_AUTO_TEST_CASE( test_two_keyranges )
{
	verifyIntersectingKeyranges(
			createDefaultKeyrange(stringLimit("aaaa", true), stringLimit("dddd", true)),
			createDefaultKeyrange(stringLimit("bbbb", true), stringLimit("eeee", true)),
			createDefaultKeyrange(stringLimit("aaaa", true), stringLimit("eeee", true))
			);

	verifyIntersectingKeyranges(
			createDefaultKeyrange(stringLimit("bbbb", true), stringLimit("eeee", true)),
			createDefaultKeyrange(stringLimit("aaaa", true), stringLimit("dddd", true)),
			createDefaultKeyrange(stringLimit("aaaa", true), stringLimit("eeee", true))
			);


	verifyIntersectingKeyranges(
			createDefaultKeyrange(negativeInfinity(), stringLimit("dddd", true)),
			createDefaultKeyrange(stringLimit("bbbb", true), positiveInfinity()),
			createDefaultKeyrange(negativeInfinity(), positiveInfinity())
			);

	verifyIntersectingKeyranges(
			createDefaultKeyrange(stringLimit("bbbb", true), positiveInfinity()),
			createDefaultKeyrange(negativeInfinity(), stringLimit("dddd", true)),
			createDefaultKeyrange(negativeInfinity(), positiveInfinity())
			);

	// this is weird but should be valid
	verifyIntersectingKeyranges(
			createDefaultKeyrange(stringLimit("aaaa", true), positiveInfinity()),
			createDefaultKeyrange(negativeInfinity(), stringLimit("eeee", true)),
			createDefaultKeyrange(negativeInfinity(), positiveInfinity())
			);

	verifyIntersectingKeyranges(
			createDefaultKeyrange(negativeInfinity(), stringLimit("eeee", true)),
			createDefaultKeyrange(stringLimit("aaaa", true), positiveInfinity()),
			createDefaultKeyrange(negativeInfinity(), positiveInfinity())
			);



	bool threw = false;
	try
		{
		verifyIntersectingKeyranges(
				createDefaultKeyrange(stringLimit("aaaa", true), stringLimit("bbbb", true)),
				createDefaultKeyrange(stringLimit("bbbb", false), stringLimit("eeee", true)),
				createDefaultKeyrange(negativeInfinity(), negativeInfinity()),
				true);
		}
	catch (std::logic_error e)
		{
		threw = true;
		}
	lassert(threw);

	threw = false;
	try
		{
		verifyIntersectingKeyranges(
				createDefaultKeyrange(stringLimit("bbbb", false), stringLimit("eeee", true)),
				createDefaultKeyrange(stringLimit("aaaa", true), stringLimit("bbbb", true)),
				createDefaultKeyrange(negativeInfinity(), negativeInfinity()),
				true);
		}
	catch (std::logic_error e)
		{
		threw = true;
		}
	lassert(threw);


}


BOOST_AUTO_TEST_CASE(test_three_keyranges)
	{
	KeyRange left = createDefaultKeyrange(stringLimit("aaaa", true), stringLimit("dddd", true));
	KeyRange right = createDefaultKeyrange(stringLimit("jjjj", true), stringLimit("oooo", true));
	KeyRange middle = createDefaultKeyrange(stringLimit("cccc", true), stringLimit("llll", true));

	KeyRangeSet s;

	s.insert(left);
	s.insert(right);
	set<KeyRange> diff = s.difference(middle);
	lassert(diff.size() == 1);
	s.insert(*diff.begin());
	lassert(s.size() == 1);
	singleKeyRangeTests(s, left);
	singleKeyRangeTests(s, right);
	singleKeyRangeTests(s, middle);
	set<KeyRange> intersection = s.intersection(createDefaultKeyrange(negativeInfinity(), positiveInfinity()));
	lassert(intersection.size() == 1);
	KeyRange result = createDefaultKeyrange(stringLimit("aaaa", true), stringLimit("oooo", true));
	lassert(result == *intersection.begin());
	}




BOOST_AUTO_TEST_SUITE_END()

	}
}

