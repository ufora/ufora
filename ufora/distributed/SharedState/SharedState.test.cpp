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
#include "View.hppml"
#include "KeyspaceManager.hppml"
#include "../../networking/InMemoryChannel.hpp"
#include "../../core/UnitTest.hpp"
#include "../../core/threading/CallbackScheduler.hppml"
#include "../../core/Clock.hpp"

#include <boost/thread.hpp>
#include <boost/lexical_cast.hpp>

using namespace SharedState;

namespace {

const char* TEST_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJ1Zm9yYSIsImV4cCI6MTM1MjkyODA0NSwiaWF0Ijo"
	"xMzUyOTI3NzQ1LCJhdWQiOiJ1cm46dWZvcmE6c2VydmljZXM6c2hhcmVkc3RhdGUiLCJwcm4iOiJ0ZXN0IiwianR"
    "pIjoiNThjZjgyYzYtNzRjZi00ZjY1LTliODktNDNhM2NiYTEzODlmIiwiYXV0aG9yaXphdGlvbnMiOlt7ImFjY2V"
    "zcyI6InJ3IiwicHJlZml4IjoiIn1dfQ.ZlvMNT8C8Iwh7NpMclzU9-XH_NOnc-5fHV-jsqCdmm0";

Keyspace getKeyspace(void)
	{
	return Keyspace("TakeHighestIdKeyType", Ufora::Json::String("data"), 1);
	}	

Key getKey(uword_t inIndex)
	{
	vector<KeyNameType> keyIndices;

	keyIndices.push_back(
		Ufora::Json::String(boost::lexical_cast<string>(inIndex))
		);

	return Key(getKeyspace(), keyIndices);
	}

bool allThreadsHaveValue(PolymorphicSharedPtr<View> inView, uword_t inThreadCount, Ufora::Json toCompare)
	{
	inView->begin();

	Keyspace keyspace("TakeHighestIdKeyType", Ufora::Json::String("data"), 1);
	
	for (long threadIndex = 0; threadIndex < inThreadCount;threadIndex++)
		{
		Key key = getKey(threadIndex);

		Nullable<ValueType> value = inView->getValue(key);

		if (!(value && value->value() && *value->value() == toCompare))
			{
			inView->end();
			return false;
			}
		}

	inView->end();
	return true;
	}

void clientThread(	PolymorphicSharedPtr<View> inView, 
					uword_t inThreadIndex, 
					uword_t inPassIndex, 
					uword_t totalThreadCount, 
					uword_t* ioSuccess
					)
	{
	std::string passIndexAsString = boost::lexical_cast<string>(inPassIndex);

	bool loginOK = inView->sendAuthorizationMessage(TEST_TOKEN, 1000);

	if (!loginOK)
		{
		LOG_WARN << "failed to authenticate in thread #" << inThreadIndex << ". failing";
		*ioSuccess = false;
		return;
		}
	
	inView->waitConnect();
	
	inView->subscribe(
		KeyRange(
			getKeyspace(),
			0,
			null(),
			null()
			),
		true //wait for success
		);

	inView->begin();

	inView->write(
		KeyUpdate(
			getKey(inThreadIndex),
			UpdateType(Ufora::Json::String(passIndexAsString))
			)
		);

	inView->end();

	//now wait until we've seen all the counts
	double t0 = curClock();

	while (!allThreadsHaveValue(inView, totalThreadCount, Ufora::Json::String(passIndexAsString)))
		{
		sleepSeconds(.1);
		if (curClock() - t0 > 5.0)
			{
			*ioSuccess = 0;
			return;
			}
		}
	
	*ioSuccess = 1;
	}

}

BOOST_AUTO_TEST_CASE( test_InMemorySharedState )
	{
	PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());

	//same test as SharedState_test.py 
	PolymorphicSharedPtr<KeyspaceManager> manager(
		new KeyspaceManager(
			0, 
			1, 
			60, 
			2, 
			"", //hmac key
			PolymorphicSharedPtr<FileStorage>()
			)
		);

	uword_t threadCount = 30;
	uword_t passCount = 10;

	for (long passIx = 0; passIx < passCount; passIx++)
		{
		std::vector<boost::shared_ptr<boost::thread> > threads;
		std::vector<uword_t> threadSuccesses;
		threadSuccesses.resize(threadCount);

		for (long threadIx = 0; threadIx < threadCount; threadIx++)
			{
			PolymorphicSharedPtr<View> newView(new View(false));


			auto pRaw = InMemoryChannel<std::string, std::string>::createChannelPair(scheduler);

			pair<channel_ptr_type, channel_type::reverse_channel_type::pointer_type> channelPair(
				makeQueuelikeChannel(
					scheduler,
					new serialized_channel_type(scheduler, pRaw.first)
					),
				makeQueuelikeChannel(
					scheduler,
					new serialized_manager_channel_type(scheduler, pRaw.second)
					)
				);
			
			newView->add(channelPair.first);
			manager->add(channelPair.second);

			threads.push_back(
				boost::shared_ptr<boost::thread>(
					new boost::thread(
						boost::bind(
							clientThread, 
							newView, 
							threadIx, 
							passIx, 
							threadCount, 
							&threadSuccesses[threadIx])
						)
					)
				);
			}

		for (long k = 0; k < threads.size();k++)
			threads[k]->join();
		
		uword_t totalSuccessCount = 0;
		for (long k = 0; k < threadSuccesses.size();k++)
			if (threadSuccesses[k])
				totalSuccessCount++;

		BOOST_CHECK_EQUAL(totalSuccessCount, threadCount);
		}
	}

