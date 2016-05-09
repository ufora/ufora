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
#include "VectorPage.hppml"
#include "../../core/StringUtil.hpp"
#include "../../core/UnitTest.hpp"
#include "../../core/threading/CallbackScheduler.hppml"
#include "VectorDataMemoryManager.hppml"
#include "VectorDataManager.hppml"
#include "../Serialization/SerializedObject.hpp"
#include "../TypedFora/ABI/ForaValueArray.hppml"

BOOST_AUTO_TEST_SUITE( test_VectorPage )

const static size_t TOTAL_AMOUNT_TO_ALLOCATE = 1024 * 1024;

const static size_t SMALL_ALLOCATION_SIZE = 1024 * 128;

namespace {
	PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());
}

BOOST_AUTO_TEST_CASE( test_page_serialization_preserves_hash )
	{
	PolymorphicSharedPtr<VectorDataManager> vdm(new VectorDataManager(scheduler, 1024 * 1024));

	//create a page and test its basic properties
	VectorPage page(vdm->getMemoryManager());

	boost::shared_ptr<Fora::Pagelet> pagelet1(new Fora::Pagelet(vdm->getMemoryManager()));
	boost::shared_ptr<Fora::Pagelet> pagelet2(new Fora::Pagelet(vdm->getMemoryManager()));

	TypedFora::Abi::ForaValueArray* array1 = pagelet1->getValues();
	TypedFora::Abi::ForaValueArray* array2 = pagelet2->getValues();

	int64_t* a1 = (int64_t*)array1->appendUninitialized(JOV::OfType(Type::Integer(64,true)), 1024).data();
	float* a2 = (float*)array2->appendUninitialized(JOV::OfType(Type::Float(32)), 512).data();

	for (long k = 0; k < 1024; k++)
		a1[k] = k;
	for (long k = 0; k < 512; k++)
		a2[k] = k;

	pagelet1->freeze();
	pagelet2->freeze();

	page.appendPagelet(pagelet1);
	page.appendPagelet(pagelet2);

	page.freeze();

	BOOST_CHECK_EQUAL(page.getPageletTree()->count(), 2);

	PolymorphicSharedPtr<SerializedObject> so1 = page.serialize();

	boost::shared_ptr<VectorPage> page2 = VectorPage::deserialize(vdm, so1);

	PolymorphicSharedPtr<SerializedObject> so2 = page2->serialize();

	BOOST_CHECK_EQUAL(page.getPageletTree()->size(), page2->getPageletTree()->size());
	for (long k = 0; k < page.getPageletTree()->size();k++)
		BOOST_CHECK(
			page.getPageletTree()->extractValueIntoFreeStore(k) ==
				page2->getPageletTree()->extractValueIntoFreeStore(k)
			);


	BOOST_CHECK(so1->hash() == so2->hash());
	}

BOOST_AUTO_TEST_CASE( test_page_serialization_preserves_size )
	{
	PolymorphicSharedPtr<VectorDataManager> vdm(new VectorDataManager(scheduler, 1024 * 1024));

	//create a page and test its basic properties
	boost::shared_ptr<VectorPage> page(new VectorPage(vdm->getMemoryManager()));

	boost::shared_ptr<Fora::Pagelet> pagelet(new Fora::Pagelet(vdm->getMemoryManager()));

	TypedFora::Abi::ForaValueArray* array1 = pagelet->getValues();

	for (long k = 0; k < 1024; k++)
		{
		array1->append(ImplValContainer());
		array1->append(ImplValContainer(CSTValue(k)));
		}

	pagelet->freeze();

	page->appendPagelet(pagelet);

	page->freeze();

	PolymorphicSharedPtr<SerializedObject> so1 = page->serialize();

	boost::shared_ptr<VectorPage> page2 = VectorPage::deserialize(vdm, so1);

	PolymorphicSharedPtr<SerializedObject> so2 = page2->serialize();

	boost::shared_ptr<VectorPage> page3 = VectorPage::deserialize(vdm, so2);

	BOOST_CHECK_LE(page2->totalBytesAllocatedFromOS(), page->totalBytesAllocatedFromOS());
	BOOST_CHECK_EQUAL(page2->totalBytesAllocatedFromOS(), page3->totalBytesAllocatedFromOS());
	}


BOOST_AUTO_TEST_CASE( test_page_serialization_of_strings )
	{
	PolymorphicSharedPtr<VectorDataManager> vdm(new VectorDataManager(scheduler, 1024 * 1024));

	//create a page and test its basic properties
	boost::shared_ptr<VectorPage> page(new VectorPage(vdm->getMemoryManager()));

	boost::shared_ptr<Fora::Pagelet> pagelet(new Fora::Pagelet(vdm->getMemoryManager()));

	TypedFora::Abi::ForaValueArray* array1 = pagelet->getValues();

	for (long k = 0; k < 100000; k++)
		array1->append(ImplValContainer(CSTValue("prefix________" + boost::lexical_cast<std::string>(k))));

	pagelet->freeze();

	page->appendPagelet(pagelet);

	page->freeze();

	auto duplicateSeveralTimes =
		[=]() {
			for (long j = 0; j < 10; j++)
				{
				PolymorphicSharedPtr<SerializedObject> so1 = page->serialize();
				boost::shared_ptr<VectorPage> page2 = VectorPage::deserialize(vdm, so1);
				}
			};

	double t0 = curClock();
	duplicateSeveralTimes();
	double singleThreadTime = curClock() - t0;


	double t1 = curClock();

	std::vector<boost::shared_ptr<boost::thread> > threads;

	for (long k = 0; k < 8; k++)
		threads.push_back(
			boost::shared_ptr<boost::thread>(
				new boost::thread(duplicateSeveralTimes)
				)
			);

	for (auto thread: threads)
		thread->join();

	double eightThreadsTime = (curClock() - t1);

	double multithreadedThroughputRatio = singleThreadTime / (eightThreadsTime / 8);

	BOOST_CHECK_MESSAGE(
		multithreadedThroughputRatio > .5,
		"Copying a million strings with 1 thread took " << singleThreadTime
			<< ". copying 8 million with 8 threads took " << eightThreadsTime
			<< ". the throughput of the multi-threaded case is "
			<< multithreadedThroughputRatio << " of the single-threaded case"
		);
	}




BOOST_AUTO_TEST_SUITE_END()

