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
#include "FastJORCoverageTable.hppml"

#include "../../../core/UnitTest.hpp"
#include "../../../core/UnitTestCppml.hpp"
#include "../../../core/Logging.hpp"
#include "../../../core/cppml/CPPMLPrettyPrinter.hppml"
#include "../../../core/math/Random.hpp"
#include "../../../core/threading/Queue.hpp"

using TypedFora::Abi::FastJORCoverageTable;

BOOST_AUTO_TEST_CASE( test_TypedFora_Abi_FastJORCoverageTable_basic )
	{
	JudgmentOnValue jovAnything = JOV() ;
	JudgmentOnValue jovTen = JOV::Constant(CSTValue((int32_t)10));
	JudgmentOnValue jovHello = JOV::Constant(CSTValue("hello"));
	JudgmentOnValue jovInteger = JOV::OfType(Type::Integer(32, true));
	JudgmentOnValue jovVectorOfAny = JOV::OfType(Type::Vector());
	JudgmentOnValue jovVectorOfInt = jovVector(JOV::OfType(Type::Integer(32, true)) );
	JudgmentOnValue jovVectorOfString = jovVector(JOV::OfType(Type::String()) );


	FastJORCoverageTable table1(
                JudgmentOnResult(emptyTreeSet() + jovInteger + jovVectorOfAny)
                );

	BOOST_CHECK_EQUAL_CPPML(table1.lookup(jovInteger), jovInteger);
	BOOST_CHECK_EQUAL_CPPML(table1.lookup(jovInteger), jovInteger);
	BOOST_CHECK_EQUAL_CPPML(table1.lookup(jovVectorOfInt), jovVectorOfAny);
	BOOST_CHECK_EQUAL_CPPML(table1.lookup(jovVectorOfInt), jovVectorOfAny);
	BOOST_CHECK_EQUAL_CPPML(table1.lookup(jovVectorOfString), jovVectorOfAny);
	BOOST_CHECK_EQUAL_CPPML(table1.lookup(jovTen), jovInteger);
	BOOST_CHECK_EQUAL_CPPML(table1.lookup(jovHello), jovAnything);
	}


BOOST_AUTO_TEST_CASE( test_TypedFora_Abi_FastJORCoverageTable_test_multithreading )
	{
	typedef TypedFora::Abi::FastJORCoverageTable hash_table_type;

	Queue<hash_table_type*> tableQueue;

	Queue<bool> hadErrorQueue;

	std::vector<JudgmentOnValue> jovs;

	jovs.push_back(JOV::OfType(Type::Integer(1, false)));
	jovs.push_back(JOV::OfType(Type::Integer(8, false)));
	jovs.push_back(JOV::OfType(Type::Integer(16, false)));
	jovs.push_back(JOV::OfType(Type::Integer(32, false)));
	jovs.push_back(JOV::OfType(Type::Integer(64, false)));
	jovs.push_back(JOV::OfType(Type::Integer(8, true)));
	jovs.push_back(JOV::OfType(Type::Integer(16, true)));
	jovs.push_back(JOV::OfType(Type::Integer(32, true)));
	jovs.push_back(JOV::OfType(Type::Integer(64, true)));

	JOV targetJOV = JOV::Unknown();

	auto insertFunction = [&](long offset) {
		while (true)
			{
			hash_table_type* table = tableQueue.get();

			//terminate if we read a null pointer
			if (!table)
				{
				//but write the null back so that all threads terminate
				tableQueue.write(table);
				return;
				}

			bool hadError = false;
			for (long k = 0; k < jovs.size(); k++)
				{
				long key = (k + offset) % jovs.size();

				JOV toLookup = jovs[key];

				if (table->lookup(toLookup) != targetJOV)
					hadError = true;
				}

			hadErrorQueue.write(hadError);
			}
		};

	std::vector<boost::thread> threads;

	for (long o = 0; o < 3; o++)
		for (long k = 0; k < 3; k++)
			threads.push_back(
				boost::thread(
					boost::bind(
						boost::function1<void, long>(insertFunction),
						o
						)
					)
				);

	double t0 = curClock();

	long count = 0;

	while (curClock() - t0 < 2.0)
		{
		count++;

		hash_table_type table(
			JudgmentOnResult(emptyTreeSet() + JOV::Unknown())
			);

		//trigger all the writer threads
		for (auto& t: threads)
			tableQueue.write(&table);

		//wait for them all to report success
		for (auto& t: threads)
			lassert(!hadErrorQueue.get());
		}

	//trigger thread termination
	tableQueue.write((hash_table_type*)0);

	for (auto& t: threads)
		t.join();
	}
