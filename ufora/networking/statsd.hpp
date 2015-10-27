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
#pragma once

#include "../core/Platform.hpp"
#ifdef BSA_PLATFORM_APPLE
#include <string>
#include <boost/thread.hpp>
#endif

namespace ufora {

class StatsdImpl;

class Statsd
{
public:
    class Timer
    {
    public:
        explicit Timer(const std::string& timer);
        Timer(Timer&& other);  // ownership transfer
        ~Timer();

        Timer& operator=(Timer&& other); // ownership transfer

        void stop();
    private:
        std::string mTimer;
        time_t mSecs;
        long mNanoSecs;
        bool mEnabled;
    };

    static void configure(
            const std::string& host,
            const std::string& port,
            const std::string& prefix="");

    Statsd();
    explicit Statsd(const std::string& component);

    void increment(const std::string& counter, uint64_t incrementBy=1);

    void decrement(const std::string& counter, uint64_t decrementBy=1);

    void gauge(const std::string& gauge, uint64_t value);

    void histogram(const std::string& histogram, uint64_t value);

    void timing(const std::string& timer, uint64_t timeInMs);

    Statsd::Timer timer(const std::string& timer);

private:
    static void initTls();
    static boost::thread_specific_ptr<StatsdImpl> tls;

    std::string prependPrefix(const std::string& metric) const;
    std::string mPrefix;
};

}

