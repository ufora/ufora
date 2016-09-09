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
#include <chrono>
#include <random>
#include "WorkerThreadPoolImpl.hppml"
#include "../FORA/VectorDataManager/VectorDataManager.hppml"
#include "../core/UnitTest.hpp"
#include "../core/UnitTestCppml.hpp"
#include "../core/threading/Queue.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "../core/math/RandomHashGenerator.hpp"



using namespace Cumulus;

namespace {
    struct TestComputation
    {
        ComputationId computationId;
        ComputationPriority priority;
        std::vector<TestComputation> dependents;

        explicit TestComputation(ComputationPriority inPriority)
                : computationId(ComputationId::CreateIdForTesting(
                    RandomHashGenerator::singleton().generateRandomHash()
                    ))
                , priority(inPriority)
            {
            }

        TestComputation(const TestComputation& other)
            : computationId(other.computationId)
            , priority(other.priority)
            , dependents(other.dependents)
            {}

        TestComputation& addDependent(TestComputation dependent)
            {
            dependents.push_back(dependent);
            return *this;
            }
    };

    ostream& operator<<(ostream& os, const TestComputation& computation)
        {
        return os << "TestComputation(computationId="
            << prettyPrintString(computation.computationId)
            << ", priority=" << prettyPrintString(computation.priority);
        }

    ComputationId getId(const TestComputation& computation)
        {
        return computation.computationId;
        }

    bool itemNotFound(
            std::set<ComputationId>& computationIds,
            const TestComputation& computation)
        {
        if (computationIds.find(computation.computationId) == computationIds.end())
            {
            computationIds.insert(computation.computationId);
            return true;
            }
        return false;
        }


    template <class InputIterator, class OutputIterator>
    void randomize_order(InputIterator begin, InputIterator end, OutputIterator out)
        {
        std::vector<TestComputation> computations;
        std::set<ComputationId> computationIds;
        for (auto i = begin; i != end; ++i)
            {
            computations.push_back(*i);
            computationIds.insert(i->computationId);
            }

        while (computations.size() > 0)
            {
            unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
            std::shuffle(computations.begin(), computations.end(), std::default_random_engine(seed));
            TestComputation computation = computations.back();
            *out = computation;
            computations.pop_back();
            size_t computationCountBefore = computations.size();
            std::copy_if(
                    computation.dependents.begin(),
                    computation.dependents.end(),
                    std::back_inserter(computations),
                    boost::bind(&itemNotFound, computationIds, _1)
                    );
            out++;
            }
        }


    //check that the dependencies of the computation at 'computationIndex' are all of
    //larger index, so that the graph is a DAG and has no cycles.
    bool verifyOrder(
            long computationIndex,
            const std::vector<TestComputation>& ordering
            )
        {
        lassert(computationIndex >= 0 && computationIndex < ordering.size());
        const TestComputation& computation = ordering[computationIndex];

        for (int i = 0; i < computation.dependents.size(); i++)
            {
            int dependentIndex;

            for (dependentIndex = 0; dependentIndex < ordering.size(); dependentIndex++)
                {
                if (ordering[dependentIndex].computationId == computation.dependents[i].computationId)
                    break;
                }

            if (dependentIndex >= ordering.size() || dependentIndex <= computationIndex)
                return false;
            }

        return true;
        }

    BOOST_AUTO_TEST_SUITE( test_Cumulus_TestComputationGeneration )

    BOOST_AUTO_TEST_CASE( test_creatingTestComputations )
        {
        TestComputation root(ComputationPriority(12UL));
        root.addDependent(TestComputation(ComputationPriority(12UL))).
            addDependent(TestComputation(ComputationPriority(12UL)).
                    addDependent(TestComputation(ComputationPriority(12UL)))
                        );
        BOOST_CHECK_EQUAL(root.dependents.size(), 2);
        BOOST_CHECK_EQUAL(root.dependents[1].dependents.size(), 1);
        }

    BOOST_AUTO_TEST_CASE( test_randomization )
        {
        std::vector<TestComputation> roots;
        roots.push_back(
            TestComputation(ComputationPriority(1UL)).
                addDependent(TestComputation(ComputationPriority(1UL))).
                addDependent(TestComputation(ComputationPriority(1UL)))
            );
        roots.push_back(
            TestComputation(ComputationPriority(2UL)).
                addDependent(TestComputation(ComputationPriority(2UL)).
                    addDependent(TestComputation(ComputationPriority(2UL))).
                    addDependent(TestComputation(ComputationPriority(2UL)))
                    )
                );

        std::vector<TestComputation> randomized;
        randomize_order(roots.begin(), roots.end(), std::back_inserter(randomized));
        BOOST_CHECK_EQUAL(randomized.size(), 7);
        for (int i = 0; i < randomized.size(); i++)
            BOOST_CHECK(randomized[0].computationId == roots[0].computationId ||
                    randomized[0].computationId == roots[1].computationId
                    );
        for (long k = 0; k < randomized.size();k++)
            BOOST_CHECK(verifyOrder(k, randomized));
        }

    BOOST_AUTO_TEST_SUITE_END()
};

class MockComputationState {
public:
    typedef boost::shared_ptr<MockComputationState> ptr_type;

    explicit MockComputationState()
        : mIsComputed(false)
        , mIsComputing(false)
        , mIsInterrupted(false)
        {}

    CreatedComputations compute(hash_type guid)
        {
        boost::mutex::scoped_lock lock(mMutex);

        if (mIsComputed)
            return CreatedComputations();

        mIsComputing = true;

        mCondition.notify_all();

        while (!mIsInterrupted && !mIsComputed)
            mCondition.wait(lock);

        if (mIsInterrupted)
            mIsInterrupted = false;

        mIsComputing = false;

        mCondition.notify_all();

        return CreatedComputations();
        }

    void interrupt()
        {
        boost::mutex::scoped_lock lock(mMutex);

        mIsInterrupted = true;

        mCondition.notify_all();
        }

    void finish()
        {
        boost::mutex::scoped_lock lock(mMutex);

        mIsComputed = true;

        mCondition.notify_all();
        }

    ComputationStatus currentComputationStatus()
        {
        boost::mutex::scoped_lock lock(mMutex);

        return (mIsComputed ? ComputationStatus::Finished() : ComputationStatus::Computable());
        }

    void waitUntilComputed() const
        {
        boost::mutex::scoped_lock lock(mMutex);

        while (!mIsComputed)
            mCondition.wait(lock);
        }

    void waitUntilComputing() const
        {
        boost::mutex::scoped_lock lock(mMutex);

        while (!mIsComputing)
            mCondition.wait(lock);
        }

    void waitUntilNotComputing() const
        {
        boost::mutex::scoped_lock lock(mMutex);

        while (mIsComputing)
            mCondition.wait(lock);
        }

    bool isComputing() const
        {
        boost::mutex::scoped_lock lock(mMutex);
        return mIsComputing;
        }

    bool isComputed() const
        {
        boost::mutex::scoped_lock lock(mMutex);
        return mIsComputed;
        }

private:
    bool mIsComputed;

    bool mIsComputing;

    bool mIsInterrupted;

    uint mSleepTime;

    mutable boost::mutex mMutex;

    mutable boost::condition_variable mCondition;
};


class MockActiveComputations {
public:
    typedef boost::shared_ptr<MockActiveComputations> ptr_type;

    explicit MockActiveComputations()
        {}

    MockActiveComputations(const MockActiveComputations& other)
        {}

    void checkinComputation(ComputationId id, CreatedComputations result)
        {
        boost::mutex::scoped_lock lock(mMutex);

        mComputations.erase(id);

        mComputationCountChanged.notify_all();
        }

    pair<MockComputationState::ptr_type, hash_type> checkoutComputation(ComputationId id)
        {
        boost::mutex::scoped_lock lock(mMutex);

        auto iter = mComputations.find(id);

        if (iter == mComputations.end())
            {
            MockComputationState::ptr_type state(new MockComputationState());
            auto insertResult = mComputations.insert(make_pair(id, state));
            BOOST_CHECK(insertResult.second);
            iter = insertResult.first;
            }

        mComputationCountChanged.notify_all();

        return make_pair(iter->second, hash_type());
        }

    void waitForComputationCountToBeNonzero()
        {
        boost::mutex::scoped_lock lock(mMutex);

        while (!mComputations.size())
            mComputationCountChanged.wait(lock);
        }

    void waitForComputationCountToReach(long count)
        {
        boost::mutex::scoped_lock lock(mMutex);

        while (mComputations.size() < count)
            mComputationCountChanged.wait(lock);
        }

    void computeAll()
        {
        while (!tryToComputeAll())
            CallbackScheduler::singletonForTesting()->blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();
        }

    bool tryToComputeAll()
        {
        boost::mutex::scoped_lock lock(mMutex);

        bool allAreComputed = true;

        for (auto it = mComputations.begin(); it != mComputations.end(); ++it)
            {
            if (!it->second->isComputed())
                {
                allAreComputed = false;
                if (it->second->isComputing())
                    {
                    it->second->finish();
                    it->second->waitUntilNotComputing();
                    }
                }
            }

        return allAreComputed;
        }

    bool computeOne()
        {
        boost::mutex::scoped_lock lock(mMutex);

        for (auto it = mComputations.begin(); it != mComputations.end(); ++it)
            {
            if (!it->second->isComputed())
                {
                if (it->second->isComputing())
                    {
                    it->second->finish();
                    it->second->waitUntilNotComputing();
                    return true;
                    }
                }
            }

        return false;
        }

    bool interruptOne()
        {
        boost::mutex::scoped_lock lock(mMutex);

        for (auto it = mComputations.begin(); it != mComputations.end(); ++it)
            {
            if (!it->second->isComputed())
                {
                if (it->second->isComputing())
                    {
                    it->second->interrupt();
                    it->second->waitUntilNotComputing();
                    return true;
                    }
                }
            }

        return false;
        }

    long computationCount()
        {
        boost::mutex::scoped_lock lock(mMutex);

        return mComputations.size();
        }

    MockComputationState::ptr_type getSingleComputationPtr()
        {
        boost::mutex::scoped_lock lock(mMutex);

        lassert(mComputations.size() == 1);

        return mComputations.begin()->second;
        }

private:
    uint mComputationDuration;

    std::map<ComputationId, MockComputationState::ptr_type> mComputations;

    boost::condition_variable mComputationCountChanged;

    boost::mutex mMutex;
};

void null_checkin(ComputationId id, CreatedComputations result)
    {
    }

LocalComputationPriorityAndStatusChanged create_computation(uint64_t priority)
    {
    return LocalComputationPriorityAndStatusChanged::Active(
        ComputationId::CreateIdForTesting(
            RandomHashGenerator::singleton().generateRandomHash()
            ),
        ComputationPriority(null() << priority),
        ComputationStatus::Computable(),
        ComputationStatistics()
        );
    }


BOOST_AUTO_TEST_SUITE( test_Cumulus_WorkerThreadPool )

typedef WorkerThreadPoolImpl<MockComputationState::ptr_type> thread_pool_type;

BOOST_AUTO_TEST_CASE( test_priority_queue )
    {
    MockActiveComputations::ptr_type activeComputations(new MockActiveComputations());

    WorkerThreadPoolImpl<MockComputationState::ptr_type> pool(
            0,
            boost::bind(&MockActiveComputations::checkoutComputation, activeComputations, _1),
            null_checkin,
            MachineId()
            );

    pool.onComputationStatusChanged(create_computation(1UL));
    pool.onComputationStatusChanged(create_computation(2UL));
    pool.onComputationStatusChanged(create_computation(0UL));

    BOOST_CHECK(pool.mComputablePriorities.size() == 3);

    BOOST_CHECK(pool.mComputablePriorities.size() == 3);

    WorkerThreadPoolImpl<MockComputationState::ptr_type>::InProgressComputationPtr
            computation = pool.selectNextComputation();

    BOOST_CHECK(computation);
    BOOST_CHECK_EQUAL_CPPML(
        computation->getComputable().priority(),
        ComputationPriority(2,0)
        );
    pool.teardown();
    }


class ComputingCallbackTracker {
public:
    ComputingCallbackTracker(
            const std::vector<LocalComputationPriorityAndStatusChanged> &expectedOrder
            )
        : mExpectedOrder(expectedOrder)
        , mActualCount(0UL)
        , mAllAreValid(true)
        , mFinished(false)
    {}

    void create(WorkerThreadPoolImpl<MockComputationState::ptr_type>::ComputablePriority computable)
        {
        LOG_DEBUG << "Computing " << prettyPrintString(computable.computationId()) << " with priority: "
            << *computable.priority().priorityLevel() << "\n";

        boost::mutex::scoped_lock lock(mMutex);

        if (mActualCount >= mExpectedOrder.size())
            {
            mAllAreValid = false;
            return;
            }

        if (mExpectedOrder[mActualCount].computation() != computable.computationId())
            mAllAreValid = false;

        if (mExpectedOrder[mActualCount].newPriority() != computable.priority())
            mAllAreValid = false;

        mActualCount++;

        if (mActualCount == mExpectedOrder.size())
            mFinished = true;
        }

    bool isFinished()
        {
        boost::mutex::scoped_lock lock(mMutex);

        return mFinished;
        }

    bool allAreValid()
        {
        boost::mutex::scoped_lock lock(mMutex);

        return mAllAreValid;
        }

private:
    boost::mutex mMutex;

    uint mActualCount;

    std::vector<LocalComputationPriorityAndStatusChanged> mExpectedOrder;

    bool mAllAreValid;

    bool mFinished;
};

BOOST_AUTO_TEST_CASE( test_start_and_stop_with_no_computations )
    {
    MockActiveComputations::ptr_type activeComputations(new MockActiveComputations());
    WorkerThreadPoolImpl<MockComputationState::ptr_type> pool(
            4,
            boost::bind(&MockActiveComputations::checkoutComputation, activeComputations, _1),
            null_checkin,
            MachineId()
            );
    pool.startComputations();
    pool.stopComputations();
    pool.teardown();
    }

BOOST_AUTO_TEST_CASE( test_worker_priority )
    {
    MockActiveComputations::ptr_type activeComputations(new MockActiveComputations());
    thread_pool_type::ptr_type pool(
            new thread_pool_type(
                1,
                boost::bind(&MockActiveComputations::checkoutComputation, activeComputations, _1),
                null_checkin,
                MachineId()
                )
            );

    std::vector<LocalComputationPriorityAndStatusChanged> expectedExecutionOrder;

    expectedExecutionOrder.push_back(create_computation(2UL));

    expectedExecutionOrder.push_back(create_computation(1UL));

    expectedExecutionOrder.push_back(create_computation(1UL));

    expectedExecutionOrder.push_back(create_computation(0UL));

    LOG_DEBUG << "Expected order:";
    for (auto i = expectedExecutionOrder.begin(); i != expectedExecutionOrder.end(); ++i)
        LOG_DEBUG << "ID: " << prettyPrintString(i->computation());

    // Create a permutation of all items that don't need to have a particular insersion order.
    std::vector<size_t> submissionOrder({0, 2, 3});

    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();

    std::shuffle(submissionOrder.begin(), submissionOrder.end(), std::default_random_engine(seed));

    ComputingCallbackTracker tracker(expectedExecutionOrder);

    pool->setComputingCallback(
        boost::bind(
            &ComputingCallbackTracker::create,
            &tracker,
            boost::arg<1>()
            )
        );

    // We push two computations with priority 1 and we want to make sure that the one submitted
    // first executes before the other.
    pool->onComputationStatusChanged(expectedExecutionOrder[1]);

    for (auto i = submissionOrder.begin(); i != submissionOrder.end(); ++i)
        {
        // Wait a little before pusing the rest of the elements to ensure that the two pri-1 items
        // don't end up with the exact same insertion timestamp
        boost::this_thread::sleep(boost::posix_time::milliseconds(1));

        pool->onComputationStatusChanged(expectedExecutionOrder[*i]);
        }

    pool->startComputations();

    while (!tracker.isFinished())
        activeComputations->computeAll();

    pool->stopComputations();

    BOOST_CHECK(tracker.allAreValid());

    pool->teardown();
    }

BOOST_AUTO_TEST_CASE( test_interrupt_computation )
    {
    MockActiveComputations::ptr_type activeComputations(new MockActiveComputations());

    Queue<ComputationId> checkinQueue;

    thread_pool_type::ptr_type pool(
            new thread_pool_type(
                1,
                boost::bind(&MockActiveComputations::checkoutComputation, activeComputations, _1),
                //checkin writes to a queue
                boost::bind(
                    &Queue<ComputationId>::write,
                    &checkinQueue,
                    boost::arg<1>()
                    ),
                MachineId()
                )
            );

    LocalComputationPriorityAndStatusChanged initialPriority = create_computation(2UL);

    pool->onComputationStatusChanged(initialPriority);

    pool->startComputations();

    activeComputations->waitForComputationCountToBeNonzero();

    MockComputationState::ptr_type state = activeComputations->getSingleComputationPtr();

    for (int i = 0; i < 5; i++)
        {
        state->waitUntilComputing();

        BOOST_CHECK_EQUAL(activeComputations->computationCount(), 1);

        BOOST_CHECK(state->isComputing());

        state->interrupt();

        checkinQueue.get();
        }

    CallbackScheduler::singletonForTesting()->blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();

    state->waitUntilComputing();

    state->finish();

    BOOST_CHECK_EQUAL(activeComputations->computationCount(), 1);

    state->waitUntilComputed();
    pool->teardown();
    }

BOOST_AUTO_TEST_CASE( test_execute_lots_of_computations )
    {
    MockActiveComputations::ptr_type activeComputations(new MockActiveComputations());

    thread_pool_type::ptr_type pool(
            new thread_pool_type(
                8,
                boost::bind(&MockActiveComputations::checkoutComputation, activeComputations, _1),
                boost::bind(&MockActiveComputations::checkinComputation, activeComputations, _1, _2),
                MachineId()
                )
            );

    pool->startComputations();

    long computed = 0;
    long created = 0;

    while (computed < 10000)
        {
        while (created < computed + 10)
            pool->onComputationStatusChanged(create_computation(created++));

        activeComputations->waitForComputationCountToReach(5);

        if (rand() > RAND_MAX / 2)
            activeComputations->interruptOne();
            else
        if (activeComputations->computeOne())
            computed++;
        }

    while (computed < created)
        if (activeComputations->computeOne())
            computed++;

    pool->teardown();
    }

BOOST_AUTO_TEST_CASE( test_verify_status_changes_during_checkin_work )
    {
    //verify that if we fire a state change off during the checkin function that
    //everything works.

    //TODO write this test
    }


BOOST_AUTO_TEST_SUITE_END()

