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
#include "../core/UnitTest.hpp"
#include "../core/math/Random.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "../networking/InMemoryChannel.hpp"
#include "../networking/SerializedChannel.hpp"
#include "../FORA/Serialization/SerializedObjectFlattener.hpp"
#include "../cumulus/CumulusWorkerToWorkerMessage.hppml"
#include "MultiChannel.hpp"
#include "OrderedMessage.hppml"


typedef InMemoryChannel<OrderedMessage<std::string>, OrderedMessage<std::string>> in_mem_string_channel;

typedef MultiChannel<std::string, std::string>               string_multi_channel;
typedef MultiChannel<std::string, std::string>::pointer_type string_multi_channel_ptr;

typedef std::pair<
            in_mem_string_channel::pointer_type,
            in_mem_string_channel::pointer_type
        > in_mem_channel_pair;

class MultiChannelTestHarness {
public:
    in_mem_channel_pair stringChannelPair1;
    in_mem_channel_pair stringChannelPair2;
    string_multi_channel_ptr multiChannel1;
    string_multi_channel_ptr multiChannel2;
    std::vector<std::tuple<size_t, uint32_t>> receivedMessagePrefixes;
    uint32_t globalMaxOrdinal;
    uint32_t writtenMessageCount;


    void blockUntilPendingHaveExecutedAndQueueIsEmpty(void)
        {
        mCallbackScheduler->blockUntilPendingHaveExecutedAndQueueIsEmpty();
        }


    MultiChannelTestHarness(PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler) :
            mCallbackScheduler(inCallbackScheduler),
            stringChannelPair1(in_mem_string_channel::createChannelPair(inCallbackScheduler)),
            stringChannelPair2(in_mem_string_channel::createChannelPair(inCallbackScheduler)),
            globalMaxOrdinal(0),
            writtenMessageCount(0)
        {
        multiChannel1.reset(
            new string_multi_channel(
                { stringChannelPair1.first, stringChannelPair2.first },
                &MultiChannelTestHarness::outgoingChannelSelector,
                mCallbackScheduler

                )
            );
        
        multiChannel2.reset(
            new string_multi_channel(
                { stringChannelPair1.second, stringChannelPair2.second},
                &MultiChannelTestHarness::outgoingChannelSelector,
                mCallbackScheduler
                )
            );

        multiChannel1->setHandlers(
            boost::bind(
                &MultiChannelTestHarness::onStringMessage,
                this,
                _1
                ),
            boost::bind(
                &MultiChannelTestHarness::onDisconnected,
                this
                )
            );
        }

    static size_t outgoingChannelSelector(const std::string& str)
        {
        return std::get<0>(parseMessagePrefix(getMessagePrefix(str)));
        }

    static uint32_t ordinalFromStringMessage(const std::string& str)
        {
        return std::get<1>(parseMessagePrefix(getMessagePrefix(str)));
        }

    static std::string getMessagePrefix(const std::string& str)
        {
        std::string prefix;
        auto separatorPos = str.find(':');
        if (separatorPos != std::string::npos)
            {
            prefix = str.substr(0, separatorPos);
            }
        return prefix;
        }

    static std::tuple<size_t, uint32_t> parseMessagePrefix(const std::string& prefix)
        {
        auto separatorPos = prefix.find(',');
        if (separatorPos != std::string::npos)
            return std::make_tuple(
                    std::stoul(prefix.substr(0, separatorPos)),
                    std::stoul(prefix.substr(separatorPos + 1))
                    );
        throw std::logic_error("not a valid message prefix");
        }

    void onStringMessage(const std::string& message)
        {
        receivedMessagePrefixes.push_back(parseMessagePrefix(getMessagePrefix(message)));
        }

    void onDisconnected()
        {
        }

    void verifyReceivedOrdinals()
        {
        BOOST_CHECK_EQUAL(receivedMessagePrefixes.size(), writtenMessageCount);

        std::map<size_t, uint32_t> maxOrdinalPerChannel;
        for (auto prefix : receivedMessagePrefixes)
            {
            size_t channelIndex;
            uint32_t messageOrdinal;
            std::tie(channelIndex, messageOrdinal) = prefix;

            uint32_t max = globalMaxOrdinal;
            globalMaxOrdinal = std::max(globalMaxOrdinal, messageOrdinal);
            if (messageOrdinal == max + 1)
                continue;

            if (maxOrdinalPerChannel.find(channelIndex) == maxOrdinalPerChannel.end())
                maxOrdinalPerChannel[channelIndex] = messageOrdinal;
            else
                {
                BOOST_REQUIRE_GT(messageOrdinal, maxOrdinalPerChannel[channelIndex]);
                maxOrdinalPerChannel[channelIndex] = messageOrdinal;
                }
            }
        }

    void write(std::string message)
        {
        multiChannel2->write(message);
        writtenMessageCount++;
        }
   
    PolymorphicSharedPtr<CallbackScheduler>    mCallbackScheduler;
};

class MultiChannelTestFixture {
public:
    MultiChannelTestFixture() : 
        scheduler(CallbackScheduler::singletonForTesting()),
        testHarness(scheduler)
        {
        }

    ~MultiChannelTestFixture()
        {
        scheduler->blockUntilPendingHaveExecutedAndQueueIsEmpty();
        testHarness.verifyReceivedOrdinals();
        testHarness.multiChannel2->disconnect();
        testHarness.multiChannel1->disconnect();
        }

    PolymorphicSharedPtr<CallbackScheduler> scheduler;
    MultiChannelTestHarness testHarness;

};


BOOST_FIXTURE_TEST_SUITE( test_MultiChannel, MultiChannelTestFixture)

BOOST_AUTO_TEST_CASE( test_1 )
    {
    testHarness.write("0,1:hello");
    testHarness.write("1,2:hello");

    testHarness.write("1,4:hello");  // this message should be delayed by the MultiChannel
                                        // until the following one, with the smaller ordinal
                                        // and on a higher priority channel, is delivered.
    testHarness.write("0,3:hello");
    }

BOOST_AUTO_TEST_CASE( test_2 )
    {
    testHarness.write("0,1:hello");
    testHarness.write("0,2:hello");
    testHarness.write("0,3:hello");
    testHarness.write("0,4:hello");
    testHarness.write("0,5:hello");
    testHarness.write("0,6:hello");
    testHarness.write("1,7:hello");
    }

BOOST_AUTO_TEST_CASE( test_3 )
    {
    testHarness.write("0,1:hello");
    testHarness.write("1,2:hello");
    
    //these messages should be delayed
    testHarness.write("1,4:hello"); 
    testHarness.write("1,5:hello"); 
    testHarness.write("1,6:hello"); 
    testHarness.write("1,7:hello"); 
    
    //and sent when we send this one:
    testHarness.write("0,3:hello");
    }

BOOST_AUTO_TEST_CASE( test_random )
    {
    for (long pass = 0; pass < 10000;pass++)
        {
        MultiChannelTestFixture fixture;

        std::vector<std::string> channel0Messages;
        std::vector<std::string> channel1Messages;

        Ufora::math::Random::Uniform<float> rnd(pass+1);

        long count = rnd() * 20 + 1;

        for (long k = 0; k < count; k++)
            if (rnd() < .5)
                channel0Messages.push_back("0," + 
                    boost::lexical_cast<string>(k) + ":hello"
                    );
            else
                channel1Messages.push_back("1," + 
                    boost::lexical_cast<string>(k) + ":hello"
                    );

        while (channel0Messages.size() || channel1Messages.size())
            {
            if (channel0Messages.size() && rnd() < .5)
                {
                fixture.testHarness.write(channel0Messages[0]);
                channel0Messages.erase(channel0Messages.begin());
                }
                else
            if (channel1Messages.size())
                {
                fixture.testHarness.write(channel1Messages[0]);
                channel1Messages.erase(channel1Messages.begin());
                }
            }
        }
    }

BOOST_AUTO_TEST_SUITE_END()


