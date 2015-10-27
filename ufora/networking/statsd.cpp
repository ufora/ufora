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
#include "../core/Exception.hpp"
#include "../core/Logging.hpp"
#include <sstream>
#include <boost/asio.hpp>

#include "../core/Platform.hpp"
#ifdef BSA_PLATFORM_APPLE
#include <mach/clock.h>
#include <mach/mach.h>
#include <mach/mach_error.h>
#endif


namespace ufora {

using boost::asio::ip::udp;

class StatsdImpl
{
public:
    StatsdImpl(const std::string& host, const std::string& port) : 
            mSocket(mIoService),
            mIsValid(false)
        {
        try {
            udp::resolver resolver(mIoService);
            udp::resolver::query query(udp::v4(), host, port, boost::asio::ip::resolver_query_base::numeric_service);
            mServerEndpoint = *resolver.resolve(query);
            mSocket.open(udp::v4());
            mIsValid = true;
            }
        catch(std::exception& e)
            {
            mIsValid = false;
            LOG_ERROR << "failed to connect StatsD to " << host << " and " << port
                << " because " << e.what();
            }
        catch(...)
            {
            mIsValid = false;
            LOG_ERROR << "failed to connect StatsD to " << host << " and " << port
                << " because of an unknown exception.";
            }
        }

    void increment(const std::string& counter, uint32_t value)
        {
        send(counter, MetricType::COUNTER, value);
        }

    void decrement(const std::string& counter, uint32_t value)
        {
        send(counter, MetricType::COUNTER, -value);
        }

    void gauge(const std::string& gauge, int64_t value)
        {
        send(gauge, MetricType::GAUGE, value);
        }

    void histogram(const std::string& histogram, int64_t value)
        {
        send(histogram, MetricType::HISTOGRAM, value);
        }

    void timing(const std::string& timer, uint64_t timeInMs)
        {
        send(timer, MetricType::TIMING, timeInMs);
        }

    static std::string host;
    static std::string port;
    static std::string prefix;

private:
    enum MetricType {
        COUNTER,
        GAUGE,
        HISTOGRAM,
        TIMING,
        SET,
        SENTINAL
        };

    static const char* metricTypes[MetricType::SENTINAL];

    void send(
            const std::string& metric,
            MetricType type,
            int64_t value,
            float sampleRate=1)
        {
        if (!mIsValid)
            return;

        std::stringstream ss;
        ss << metric << ':' << value << '|' << metricTypes[type];

        try
            {
            mSocket.async_send_to(
                boost::asio::buffer( ss.str() ),
                mServerEndpoint,
                &StatsdImpl::asyncSendCallback
                );
            }
        catch(std::exception& e)
            {
            LOG_ERROR << "Failed to send stats. Message: " << ss.str()
                      << ". Error: " << e.what();
            }
        }

    static void asyncSendCallback(
            const boost::system::error_code& error,
            std::size_t bytes_transferred
            )
        {
        if (error)
            LOG_ERROR << "Failed to async send statsd udp packet: " << error.message();
        }
        

    boost::asio::io_service mIoService;
    
    udp::socket mSocket;
    
    udp::endpoint mServerEndpoint;

    bool mIsValid;
};

std::string StatsdImpl::host = "localhost";
std::string StatsdImpl::port = "8125";
std::string StatsdImpl::prefix = "";
const char* StatsdImpl::metricTypes[StatsdImpl::MetricType::SENTINAL] = {"c", "g", "h", "ms", "s"};


boost::thread_specific_ptr<StatsdImpl> Statsd::tls;

void Statsd::configure(const std::string& host, const std::string& port, const std::string& prefix)
    {
    StatsdImpl::host = host;
    StatsdImpl::port = port;
    StatsdImpl::prefix = prefix;
    }

/////////////////////////////////////////////
// class Statsd::Timer
/////////////////////////////////////////////
Statsd::Timer::Timer(const std::string& timer)
    : mTimer(timer)
    , mEnabled(true)
    {
    #ifdef BSA_PLATFORM_APPLE
        // Naively copied from http://stackoverflow.com/questions/11680461/monotonic-clock-on-osx
        clock_serv_t cclock;
        mach_timespec_t mts;
        kern_return_t ret;

        host_get_clock_service(mach_host_self(), SYSTEM_CLOCK, &cclock);
        ret = clock_get_time(cclock, &mts);
        if (ret != KERN_SUCCESS)
            throw Ufora::Exception("Failed to get current time with Mach clock_get_time.");
        mSecs = mts.tv_sec;
        mNanoSecs = mts.tv_nsec;
        mach_port_deallocate(mach_task_self(), cclock);
    #else
        timespec ts;
        if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) != 0)
            throw Ufora::PosixException("Failed to get current time with clock_gettime.", errno);
        mSecs = ts.tv_sec;
        mNanoSecs = ts.tv_nsec;
    #endif
    }

Statsd::Timer::Timer(Timer&& other)
    : mTimer(other.mTimer)
    , mSecs(other.mSecs)
    , mNanoSecs(other.mNanoSecs)
    , mEnabled(true)
    {
    // trnasfer ownership from other to this
    other.mEnabled = false;
    }

Statsd::Timer::~Timer()
    {
    if (mEnabled)
        stop();
    }

Statsd::Timer& Statsd::Timer::operator=(Statsd::Timer&& other)
    {
    mTimer = other.mTimer;
    mSecs = other.mSecs;
    mNanoSecs = other.mNanoSecs;
    mEnabled = true;

    other.mEnabled = false;
    return *this;
    }

void Statsd::Timer::stop()
    {
    time_t secs;
    long nanoSecs;

    #ifdef BSA_PLATFORM_APPLE
        // Naively copied from http://stackoverflow.com/questions/11680461/monotonic-clock-on-osx
        clock_serv_t cclock;
        mach_timespec_t mts;
        kern_return_t ret;

        host_get_clock_service(mach_host_self(), SYSTEM_CLOCK, &cclock);
        ret = clock_get_time(cclock, &mts);
        if (ret != KERN_SUCCESS)
            throw Ufora::Exception("Failed to get current time with Mach clock_get_time.");

        secs = mts.tv_sec;
        nanoSecs = mts.tv_nsec;
        mach_port_deallocate(mach_task_self(), cclock);
    #else
        timespec ts;
        if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) != 0)
            return;

        secs = ts.tv_sec - mSecs;
        nanoSecs = ts.tv_nsec - mNanoSecs;
    #endif

    uint64_t millisecs = secs*1000 + nanoSecs/1000000;
    initTls();

    tls->timing(mTimer, millisecs);
    mEnabled = false;
    }


/////////////////////////////////////////////
// class Statsd
/////////////////////////////////////////////
void Statsd::initTls()
    {
    if (!tls.get())
        {
        tls.reset(new StatsdImpl(StatsdImpl::host, StatsdImpl::port));
        }
    }

Statsd::Statsd() : mPrefix(StatsdImpl::prefix)
    {
    }

Statsd::Statsd(const std::string& component) :
        mPrefix(StatsdImpl::prefix + (StatsdImpl::prefix.size() ? "." : "") +
                component + (component.size() ? "." : "")
               )
    {
    }

void Statsd::increment(const std::string& counter, uint64_t incrementBy)
    {
    initTls();
    tls->increment(prependPrefix(counter), incrementBy);
    }

void Statsd::decrement(const std::string& counter, uint64_t decrementBy)
    {
    initTls();
    tls->decrement(prependPrefix(counter), decrementBy);
    }

void Statsd::gauge(const std::string& gauge, uint64_t value)
    {
    initTls();
    tls->gauge(prependPrefix(gauge), value);
    }

void Statsd::histogram(const std::string& histogram, uint64_t value)
    {
    initTls();
    tls->histogram(prependPrefix(histogram), value);
    }

void Statsd::timing(const std::string& timer, uint64_t timeInMs)
    {
    initTls();
    tls->timing(prependPrefix(timer), timeInMs);
    }

Statsd::Timer Statsd::timer(const std::string& timer)
    {
    return Timer(prependPrefix(timer));
    }

std::string Statsd::prependPrefix(const std::string& metric) const
    {
    return mPrefix + "." + metric;
    }

}

