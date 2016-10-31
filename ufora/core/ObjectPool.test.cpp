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
#include "ObjectPool.hpp"
#include "UnitTest.hpp"

namespace Ufora {

class ObjectPoolTestFixture {
public:
    ObjectPoolTestFixture() :
            pool(
                boost::function0<boost::shared_ptr<long> >(
                    []() {
                        return boost::shared_ptr<long>(new long());
                        }
                    )
                )
        {
        }

    ObjectPool<long> pool;
};

BOOST_FIXTURE_TEST_SUITE( test_ObjectPool, ObjectPoolTestFixture )

BOOST_AUTO_TEST_CASE( test_construction )
    {
    ObjectPool<long>::Handle h;

    BOOST_CHECK(!h);

    h = pool.get();

    BOOST_CHECK(h);

    h = ObjectPool<long>::Handle();
    }

BOOST_AUTO_TEST_CASE( test_object_lifetime )
    {
    ObjectPool<long>::Handle h;

        {
        ObjectPool<long> anotherPool(
            boost::function0<boost::shared_ptr<long> >(
                []() {
                    return boost::shared_ptr<long>(new long());
                    }
                )
            );

        h = anotherPool.get();
        }

    *h = 10;

    BOOST_CHECK(*h == 10);
    }

BOOST_AUTO_TEST_CASE( test_handle_copying )
    {
    auto h1 = pool.get();

    auto h2 = pool.get();

    auto h3 = h2;

    //h1 and h2 should be different longs
    BOOST_CHECK(&*h1 != &*h2);

    //h2 and h3 should be the same
    BOOST_CHECK(&*h2 == &*h3);
    }

BOOST_AUTO_TEST_CASE( test_handle_checkin_and_out )
    {
    auto h1 = pool.get();

    *h1 = 1234;

    h1 = ObjectPool<long>::Handle();

    BOOST_CHECK(!h1);

    //there should only be one handle, so the value we wrote should persist.
    auto h2 = pool.get();

    BOOST_CHECK(*h2 == 1234);
    }

BOOST_AUTO_TEST_SUITE_END( )
}

