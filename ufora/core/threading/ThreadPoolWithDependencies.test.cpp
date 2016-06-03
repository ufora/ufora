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
#include "ThreadPoolWithDependencies.hpp"
#include "../UnitTest.hpp"
#include "../containers/ImmutableTreeSet.hppml"
#include "Queue.hpp"

namespace Ufora {

BOOST_AUTO_TEST_SUITE( test_ThreadPoolWithDependencies )

BOOST_AUTO_TEST_CASE( test_construction )
    {
    ThreadPoolWithDependencies<> pool(1);
    }

BOOST_AUTO_TEST_CASE( test_execute_a_task )
    {
    ThreadPoolWithDependencies<> pool(1);

    Queue<long> resultQueue;

    pool.addTask(
        "task",
        boost::function0<void>(
            [&]() { resultQueue.write(0); }
            ),
        0,
        std::set<std::string>(),
        false
        );

    long res = 0;

    BOOST_CHECK(resultQueue.getTimeout(res, 1.0));
    BOOST_CHECK(res == 0);
    }

BOOST_AUTO_TEST_CASE( test_out_of_order_definition )
    {
    ThreadPoolWithDependencies<> pool(1);

    Queue<long> resultQueue;

    pool.addTask(
        "task",
        boost::function0<void>(
            [&]() { resultQueue.write(0); }
            ),
        0,
        ImmutableTreeSet<std::string>() + std::string("subtask"),
        false
        );

    long res = 0;

    //we shouldn't be able to complete
    BOOST_CHECK(!resultQueue.getTimeout(res, .01));

    pool.addTask(
        "subtask",
        boost::function0<void>(
            [&]() { resultQueue.write(1); }
            ),
        0,
        ImmutableTreeSet<std::string>(),
        false
        );

    //now the subtask should execute first (so we get a 1)
    BOOST_CHECK(resultQueue.getTimeout(res, 1.0));
    BOOST_CHECK(res == 1);

    //and then the main task
    BOOST_CHECK(resultQueue.getTimeout(res, 1.0));
    BOOST_CHECK(res == 0);
    }

BOOST_AUTO_TEST_CASE( test_task_tree )
    {
    ThreadPoolWithDependencies<long> pool(4);

    Queue<long> resultQueue;

    const static long testSize = 10000;

    for (long k = 0; k < testSize;k++)
        {
        std::set<long> deps;

        if (k/2 < k)
            deps.insert(k/2);
        if (k/2+1 < k)
            deps.insert(k/2+1);

        pool.addTask(
            k,
            boost::function0<void>(
                boost::bind(
                    boost::function1<void, long>(
                        [&](long k) {
                            if (k/2 < k)
                                lassert(pool.hasTaskExecuted(k/2));
                            if (k/2+1 < k)
                                lassert(pool.hasTaskExecuted(k/2+1));

                            resultQueue.write(k);

                            sleepSeconds(.0001);
                            }
                        ),
                    k
                    )
                ),
            0,
            deps,
            false
            );
        }

    long res = 0;

    std::set<long> finished;

    while (finished.size() < testSize)
        {
        lassert(resultQueue.getTimeout(res, 1.0));
        finished.insert(res);
        }
    }

BOOST_AUTO_TEST_SUITE_END( )
}

