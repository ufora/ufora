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

#include "Channel.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "../core/InstanceCounter.hpp"

template<class TOut, class TIn, 
			class serializer_type = BinaryStreamSerializer, 
			class deserializer_type = BinaryStreamDeserializer
			>
class SerializedChannel : public Channel<TOut, TIn>, InstanceCounter<SerializedChannel<TOut, TIn> > {
public:
	typedef PolymorphicSharedPtr<
				SerializedChannel<TOut, TIn, serializer_type, deserializer_type>, 
				typename Channel<TOut, TIn>::pointer_type
			> pointer_type;

	typedef PolymorphicSharedWeakPtr<
				SerializedChannel<TOut, TIn, serializer_type, deserializer_type>, 
				typename Channel<TOut, TIn>::weak_ptr_type
			> weak_ptr_type;

	typedef PolymorphicSharedPtr<
				SerializedChannel<TIn, TOut, serializer_type, deserializer_type>, 
				typename Channel<TIn, TOut>::pointer_type
			> reverse_pointer_type;

	typedef PolymorphicSharedWeakPtr<
				SerializedChannel<TIn, TOut, serializer_type, deserializer_type>, 
				typename Channel<TIn, TOut>::weak_ptr_type
			> weak_reverse_pointer_type;
	

	SerializedChannel(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				PolymorphicSharedPtr<Channel<std::string, std::string> > inInnerChannel
				) : 
			mCallbackScheduler(inCallbackScheduler),
			mInnerChannel(inInnerChannel),
			mIsDisconnected(false)
		{
		}

	virtual std::string channelType()
		{
		return "SerializedChannel<" + mInnerChannel->channelType() + ">";
		}

	SerializedObjectStream<serializer_type>& getSerializer()
		{
		return mSerializer;
		}

	DeserializedObjectStream<deserializer_type>& getDeserializer()
		{
		return mDeserializer;
		}

	void setCallbackScheduler(PolymorphicSharedPtr<CallbackScheduler> inScheduler)
		{
		boost::mutex::scoped_lock lock(mSchedulerMutex);

		mCallbackScheduler = inScheduler;
		}

	PolymorphicSharedPtr<CallbackScheduler> getScheduler()
		{
		return mCallbackScheduler;
		}

	virtual void disconnect(void)
		{
			{
			boost::recursive_mutex::scoped_lock lock(mDisconnectMutex);

			if (mIsDisconnected)
				return;

			mIsDisconnected = true;
			}
		
		getCallbackScheduler()->scheduleImmediately(
			boost::bind(
				disconnectChannelPreHop,
				this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>(),
				mInnerChannel
				),
			"SerializedChannel::disconnect"
			);
		}

	virtual void write(const TOut& in)
		{
		getCallbackScheduler()->scheduleImmediately(
			boost::bind(
				serialize,
				this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>(),
				in
				),
			"SerializedChannel::write"
			);
		}

	void setHandlers(
				boost::function1<void, TIn> inOnMessage, 
				boost::function0<void> inOnDisconnected
				)
		{
		using namespace boost;


		mInnerChannel->setHandlers(
			boost::bind(
				callInteriorInOnMessage,
				weak_ptr_type(
					this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>()
					),
				getCallbackScheduler(),
				inOnMessage,
				_1
				),
			boost::bind(
				scheduleOnDisconnected,
				inOnDisconnected,
				getCallbackScheduler()
				)
			);
		}
private:
	static void serialize(pointer_type ptr, TOut in)
		{
		ptr->serialize(in);
		}

	void serialize(const TOut& in)
		{
		boost::recursive_mutex::scoped_lock lock(mSerializeMutex);

		std::string toWrite = mSerializer.serialize(in);
		
		getCallbackScheduler()->scheduleImmediately(
			boost::bind(
				writeToChannel,
				this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>(),
				mInnerChannel,
				toWrite
				),
			"SerializedChannel::write"
			);
		}

	static void scheduleOnDisconnected(
			boost::function0<void> toSchedule,
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
			)
		{
		inCallbackScheduler->scheduleImmediately(
			toSchedule,
			"SerializedChannel::scheduleOnDisconnected"
			);
		}


	static void disconnectChannelPreHop(
						pointer_type ptr,
						PolymorphicSharedPtr<Channel<std::string, std::string> > inChannel
						)
		{
		ptr->getCallbackScheduler()->scheduleImmediately(
			boost::bind(
				disconnectChannel,
				ptr,
				inChannel
				),
			"SerializedChannel::disconnect"
			);
		}

	static void disconnectChannel(
						pointer_type ptr,
						PolymorphicSharedPtr<Channel<std::string, std::string> > inChannel
						)
		{
		inChannel->disconnect();
		}

	static void writeToChannel(
					pointer_type ptr,
					PolymorphicSharedPtr<Channel<std::string, std::string> > channel,
					std::string s
					)
		{
		try {
			channel->write(s);
			}
		catch(const ChannelDisconnected&)
			{
			}
		}

	static void callInOnMessage(
				pointer_type ptr,
				boost::function1<void, TIn> inOnMesssage,
				TIn value
				)
		{
		try {
			inOnMesssage(value);
			}
		catch(const ChannelDisconnected&)
			{
			}
		}

	static void callInteriorInOnMessage(
				weak_ptr_type inPtr,
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				boost::function1<void, TIn> inOnMesssage,
				std::string inString
				)
		{
		pointer_type ptr = inPtr.lock();

		if (!ptr)
			return;

		boost::recursive_mutex::scoped_lock lock(ptr->mDeserializeMutex);

		double t0 = curClock();

		TIn value = ptr->mDeserializer.template deserialize<TIn>(inString);
		
		if (curClock() - t0 > .1)
			LOG_INFO << "Took " << curClock() - t0 << " to deserialize " 
				<< inString.size() / 1024 / 1024.0 << " MB."
				<< " into "
				<< Ufora::debug::StackTrace::demangle(typeid(TIn).name())
				;
		
		inCallbackScheduler->scheduleImmediately(
			boost::bind(
				callInOnMessage,
				ptr,
				inOnMesssage,
				value
				),
			"SerializedChannel::callInteriorInOnMessage"
			);
		}

	PolymorphicSharedPtr<CallbackScheduler> getCallbackScheduler()
		{
		boost::mutex::scoped_lock lock(mSchedulerMutex);

		return mCallbackScheduler;
		}

	boost::mutex mSchedulerMutex;

	PolymorphicSharedPtr<CallbackScheduler> mCallbackScheduler;

	boost::recursive_mutex mDeserializeMutex, mSerializeMutex;

	SerializedObjectStream<serializer_type> mSerializer;

	DeserializedObjectStream<deserializer_type> mDeserializer;
	
	PolymorphicSharedPtr<Channel<std::string, std::string> > mInnerChannel;

	boost::recursive_mutex mDisconnectMutex;

	bool mIsDisconnected;
};


