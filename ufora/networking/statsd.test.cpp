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
#include "statsd.hpp"
#include "../core/UnitTest.hpp"

namespace ufora {

BOOST_AUTO_TEST_SUITE( test_statsd)


BOOST_AUTO_TEST_CASE( test_counter )
    {
    Statsd::configure("localhost", "8125");

    Statsd stats;
    stats.increment("test.unit.counter");
    stats.increment("test.unit.counter", 5);
    stats.decrement("test.unit.counter");
    stats.decrement("test.unit.counter", 2);
    stats.increment("test.unit.counter", 50);
    }


BOOST_AUTO_TEST_CASE( test_timer )
    {
    Statsd stats;
    for (int i=0; i < 10; i++)
        {
        auto timer = stats.timer("test.unit.timer");
        boost::this_thread::sleep( boost::posix_time::milliseconds(100) );
        }
    }

BOOST_AUTO_TEST_SUITE_END( )
}

