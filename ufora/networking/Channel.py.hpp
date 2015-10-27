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
#include <stdint.h>
#include <boost/python.hpp>
#include "Channel.hpp"
#include "QueuelikeChannel.hppml"
#include "InMemoryChannel.hpp"
#include "SerializedChannel.hpp"
#include "RateLimitedChannelGroup.hpp"

#include <stdint.h>
#include <boost/python.hpp>
#include "../native/Registrar.hpp"
#include "../core/python/CPPMLWrapper.hpp"
#include "../core/python/ScopedPyThreads.hpp"
#include "../core/threading/CallbackScheduler.hppml"

template<class TOut, class TIn>
class ChannelWrapper :
	public native::module::Exporter<ChannelWrapper<TOut, TIn> > {
public:
	ChannelWrapper(std::string inName) :  mName(inName)
		{
		}

	std::string		getModuleName(void)
		{
		return mName;
		}

	typedef typename QueuelikeChannel<TOut, TIn>::pointer_type queuelike_channel_ptr_type;

	typedef typename Channel<TOut, TIn>::pointer_type channel_ptr_type;

	typedef typename Channel<TIn, TOut>::pointer_type reverse_channel_ptr_type;

	static TIn QueuelikeChannelGet(
						queuelike_channel_ptr_type& inChannel
						)
		{
		ScopedPyThreads releasePythonGIL;

		return inChannel->get();
		}

	static boost::python::object QueuelikeChannelGetNonblocking(
						queuelike_channel_ptr_type& inChannel
						)
		{
		TIn out;

		bool hasValue = false;

			{
			ScopedPyThreads releasePythonGIL;

			hasValue = inChannel->get(out);
			}

		if (hasValue)
			return boost::python::object(out);

		return boost::python::object();
		}

	static boost::python::object QueuelikeChannelGetTimeout(
						queuelike_channel_ptr_type& inChannel,
						double timeout
						)
		{
		TIn out;

		bool hasValue = false;

			{
			ScopedPyThreads releasePythonGIL;

			hasValue = inChannel->getTimeout(out, timeout);
			}

		if (hasValue)
			return boost::python::object(out);
		
		return boost::python::object();
		}

	static void QueuelikeChannelWrite(
						queuelike_channel_ptr_type& inChannel,
						TOut toWrite
						)
		{
		ScopedPyThreads releasePythonGIL;

		return inChannel->write(toWrite);
		}

	static void QueuelikeChannelDisconnect(
						queuelike_channel_ptr_type& inChannel
						)
		{
		return inChannel->disconnect();
		}

	static void ChannelWrite(
						channel_ptr_type& inChannel,
						TOut toWrite
						)
		{
		ScopedPyThreads releasePythonGIL;

		return inChannel->write(toWrite);
		}

	static void ChannelDisconnect(
						channel_ptr_type& inChannel
						)
		{
		inChannel->disconnect();
		}

	static bool QueuelikeChannelHasPendingValues(
						queuelike_channel_ptr_type& inChannel
						)
		{
		return inChannel->hasPendingValues();
		}


	static boost::python::object makeQueuelikeInMemoryChannel(
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
			)
		{
		auto p = InMemoryChannel<TOut, TIn>::createChannelPair(inCallbackScheduler);

		return boost::python::make_tuple(
			makeQueuelikeChannel(inCallbackScheduler, channel_ptr_type(p.first)),
			makeQueuelikeChannel(inCallbackScheduler, reverse_channel_ptr_type(p.second))
			);
		}		

	static boost::python::object makeInMemoryChannel(
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
			)
		{
		auto p = InMemoryChannel<TOut, TIn>::createChannelPair(inCallbackScheduler);

		return boost::python::make_tuple(
			channel_ptr_type(p.first),
			reverse_channel_ptr_type(p.second)
			);
		}

	static boost::python::object ChannelMakeQueuelikeChannel(
			channel_ptr_type inPtr,
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler)
		{
		return boost::python::object(makeQueuelikeChannel(inCallbackScheduler, inPtr));
		}

	void	getDefinedTypes(std::vector<std::string>& outTypes)
		{
		outTypes.push_back(typeid(typename QueuelikeChannel<TOut, TIn>::pointer_type).name());
		outTypes.push_back(typeid(typename Channel<TOut, TIn>::pointer_type).name());
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;

		class_<typename Channel<TOut, TIn>::pointer_type>(mName.c_str(), no_init)
			.def("write", &ChannelWrite)
			.def("disconnect", &ChannelDisconnect)
			.def("makeQueuelike", &ChannelMakeQueuelikeChannel)
			;

		class_<typename QueuelikeChannel<TOut, TIn>::pointer_type,
				boost::python::bases<
					typename Channel<TOut, TIn>::pointer_type
					>
				>(("Queuelike" + std::string(mName)).c_str(), no_init)
			.def("get", &QueuelikeChannelGet)
			.def("getNonblocking", &QueuelikeChannelGetNonblocking)
			.def("getTimeout", &QueuelikeChannelGetTimeout)
			.def("write", &QueuelikeChannelWrite)
			.def("disconnect", &QueuelikeChannelDisconnect)
			.def("hasPendingValues", &QueuelikeChannelHasPendingValues)
			;

		def(("InMemory" + std::string(mName)).c_str(), makeInMemoryChannel);

		def(("QueuelikeInMemory" + std::string(mName)).c_str(), makeQueuelikeInMemoryChannel);
		}
private:
	std::string mName;
};


