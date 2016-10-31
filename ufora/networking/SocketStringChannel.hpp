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
#ifndef SocketChannel_hpp
#define SocketChannel_hpp

#include <sstream>
#include <errno.h>
#include <boost/bind.hpp>

#include "../core/lassert.hpp"
#include "../core/Logging.hpp"
#include "../core/serialization/Serialization.hpp"
#include "../core/threading/BSAThread.hpp"
#include "../core/math/Hash.hpp"
#include "../core/Platform.hpp"
#include "../core/cppml/CPPMLPrettyPrinter.hppml"

#include "FileDescriptorRegistry.hpp"
#include "Channel.hpp"
#include "QueuelikeChannel.hppml"
#include "InMemoryChannel.hpp"


#if defined(BSA_PLATFORM_LINUX)

#include <sys/socket.h>

#elif defined(BSA_PLATFORM_APPLE)

#include <sys/socket.h>

#ifndef MSG_NOSIGNAL
// MSG_NOSIGNAL isn't defined for Mac; use SO_NOSIGPIPE.
#define MSG_NOSIGNAL SO_NOSIGPIPE
#endif

#elif defined(BSA_PLATFORM_WINDOWS)

#include <winsock2.h>

#endif


using namespace std;

class SocketStringChannel : public Channel<string, string> {
public:
	typedef PolymorphicSharedPtr<SocketStringChannel, Channel<string, string>::pointer_type> pointer_type;

	typedef PolymorphicSharedWeakPtr<SocketStringChannel, Channel<string, string>::weak_ptr_type> weak_ptr_type;

	SocketStringChannel(PolymorphicSharedPtr<CallbackScheduler> inScheduler, int32_t inFileDescriptor) :
			mCallbackScheduler(inScheduler),
			mFileDescriptor(inFileDescriptor),
			mIsDisconnected(false),
			mThreadsStarted(false),
			mQueuedItemsToWritePtr(new Queue<Nullable<std::string> >()),
			mOnDisconnected(&SocketStringChannel::defaultDisconnectHandler),
			mHandlersSet(false)
		{
		mBytesWritten = 0;
		}

	virtual std::string channelType()
		{
		return "SocketStringChannel";
		}

	virtual void disconnect(void)
		{
		boost::recursive_mutex::scoped_lock scopedLock(mMutex);

		if (!mIsDisconnected)
			{
			// we only want to disconnect from one thread a single time so if we find
			// out that lock is false, then someone else is actively disconnecting and
			// we should bail.
			mIsDisconnected = true;

			LOG_INFO << "SocketStringChannel disconnecting. Closing file descriptor"
				<< mFileDescriptor
				<< "\n"
				;

			mQueuedItemsToWritePtr->write(null());

			int err;

			err = shutdown(mFileDescriptor, SHUT_RDWR);

			if (err != 0)
				LOG_WARN << "Error shutting down socket\n" << strerror(errno);

			if (mThreadsStarted)
				{
				scopedLock.unlock();

				if (!Ufora::thread::currentlyOnThread(mWriteThread))
					Ufora::thread::joinThread(mWriteThread);

				if (!Ufora::thread::currentlyOnThread(mReadThread))
					Ufora::thread::joinThread(mReadThread);

   				scopedLock.lock();
				}

			err = close(mFileDescriptor);
			if (err != 0)
				LOG_WARN << "Error closing socket\n" << strerror(errno);


			scopedLock.unlock();

			try {
				mOnDisconnected();
				}
			catch(std::exception& e)
				{
				LOG_ERROR << "mOnDisconnected threw an exception: " << e.what();
				abort();
				}
			catch(...)
				{
				LOG_ERROR << "mOnDisconnected threw an unknown exception";
				abort();
				}

			}
		}

	virtual void write(const string& in)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (mIsDisconnected)
			throw ChannelDisconnected();

		updateBytesWritten(in);

		mQueuedItemsToWritePtr->write(null() << in);
		}


	void setHandlers(
				boost::function1<void, std::string> inOnMessage,
				boost::function0<void> inOnDisconnected
				)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		mOnMessage = inOnMessage;
		mOnDisconnected = inOnDisconnected;

		mHandlersSet = true;

		if (mIsDisconnected)
			inOnDisconnected();

		ensureThreadsStarted();
		}

	void setDescription(string desc)
		{
		mDescription = desc;
		}

private:
	void ensureThreadsStarted(void)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (mThreadsStarted || mIsDisconnected)
			return;

		mThreadsStarted = true;

		const size_t kStackSize = 128 * 1024;

		pointer_type ptr = polymorphicSharedPtrFromThis().dynamic_pointer_cast<pointer_type>();

		weak_ptr_type weakToThis(ptr);

		mReadThread = Ufora::thread::spawnThread(
			boost::bind(
				readloopStatic,
				weakToThis
				),
			kStackSize
			);

		mWriteThread = Ufora::thread::spawnThread(
			boost::bind(writeloopStatic,
				weakToThis
				),
			kStackSize
			);

		LOG_DEBUG << "Created SocketStringChannel " << (uword_t)this;
		}

	void setCallbackScheduler(PolymorphicSharedPtr<CallbackScheduler> inScheduler)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		mCallbackScheduler = inScheduler;
		}

	PolymorphicSharedPtr<CallbackScheduler> getScheduler()
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		return mCallbackScheduler;
		}

	void onMessage(const std::string& stringToWrite)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (!mIsDisconnected)
			mCallbackScheduler->scheduleImmediately(
				boost::bind(
					mOnMessage,
					stringToWrite
					),
				"SocketStringChannel::onMessage"
				);
		}

	void updateBytesWritten(const string& stringToWrite)
		{
		int64_t bytesToWrite = stringToWrite.size() + sizeof(int32_t);

		if (shouldLogBytesWritten(bytesToWrite))
			LOG_DEBUG << mDescription << ": bytes written: " << mBytesWritten + bytesToWrite;

		mBytesWritten += bytesToWrite;
		}

	bool shouldLogBytesWritten(int64_t bytesToWrite)
		{
		return ((mBytesWritten + bytesToWrite) / 100000 != (mBytesWritten / 100000));
		}

	template<class T>
	void read(T& out, int32_t fd)
		{
		readBytes(fd, &out, sizeof(T));
		}

	template<class T>
	void write(const T& out, int32_t fd)
		{
		writeBytes(fd, (void*) &out, sizeof(T));
		}

	void readBytes(int32_t fd, void *data, uint32_t bytes)
		{
		int32_t bytesRead = 0;
		double totalWaitTime = 0.0;
		double nextSleepPeriod = 0.001;


		while (bytesRead < bytes)
			{
			int32_t res = recv(fd, ((char*)data) + bytesRead, bytes - bytesRead, MSG_WAITALL);
			if (res <= 0)
				{
				int err = errno;

				if (res == 0)
					throw ChannelDisconnected();

				if (err == EAGAIN || err == EINTR || err == EWOULDBLOCK)
					{
					if (mIsDisconnected)
						throw ChannelDisconnected();

					lassert_dump(
						totalWaitTime <= 10.0,
						"Somehow we got into an infinite receive loop. res = " << res
						<< ". errno = " << strerror(err)
						)
					if (nextSleepPeriod >= 1.0)
						LOG_WARN << "Sleep period after failure to recv from socket reached " << nextSleepPeriod
							<< " seconds";

					sleepSeconds(nextSleepPeriod);
					totalWaitTime += nextSleepPeriod;
					nextSleepPeriod = std::min(1.0, 2*nextSleepPeriod);
					}
				else
					{
					if (res != 0)
						LOG_WARN << "Disconnecting a SocketStringChannel during read because of error "
							<< strerror(err) << ". " << bytesRead << " read out of "
							<< bytes << " expected."
							;
					LOG_DEBUG << "Disconnecting a SocketStringChannel because res is " << res;

					throw ChannelDisconnected();
					}
				}
			else
				{
				totalWaitTime = 0.0;
				nextSleepPeriod = 0.001;
				bytesRead += res;
				}
			}
		lassert(bytesRead == bytes);
		}

	void writeBytes(int32_t fd, void *data, uint32_t bytes)
		{
		int32_t bytesWritten = 0;
		while (bytesWritten < bytes)
			{
			//use MSG_NOSIGNAL, which will prevent a SIGPIPE signal from being sent to our process,
			//which we don't currently handle anywhere.  We will still get EPIPE if the other end is
			//closed.
			int32_t res = send(fd, ((char*)data) + bytesWritten, bytes - bytesWritten, MSG_NOSIGNAL);
			if (res <= 0)
				{
				if (errno == EAGAIN || errno == EINTR || errno == EWOULDBLOCK)
					{
					if (mIsDisconnected)
						throw ChannelDisconnected();

					boost::thread::yield();
					}
				else
					{
					if (res != 0)
						LOG_DEBUG << "Disconnecting a SocketStringChannel during write because of error "
							<< strerror(errno) << ". " << bytesWritten << " written out of "
							<< bytes << " expected."
							;

					throw ChannelDisconnected();
					}
				}
			else
				bytesWritten += res;
			}
		lassert(bytesWritten == bytes);
		}

	static void writeloopStatic(
					weak_ptr_type weakSocketPtr
					)
		{
		pointer_type socket = weakSocketPtr.lock();

		if (!socket)
			return;

		socket->writeLoop();
		}

	//lock the file descriptor, but wait in case the OS has the FD but we're still unregistering
	//it in another thread.
	static boost::shared_ptr<ScopedFileDescriptorRegisterer> getFdRegistrar(int fd)
		{
		boost::shared_ptr<ScopedFileDescriptorRegisterer> fdRegisterer(
			new ScopedFileDescriptorRegisterer(fd, 2)
			);

		long tries = 0;
		while (!fdRegisterer->sucessfullyRegistered())
			{
			if (tries > 10)
				{
				return boost::shared_ptr<ScopedFileDescriptorRegisterer>();
				}
			else
				{
				sleepSeconds(.1);
				tries++;
				fdRegisterer.reset(new ScopedFileDescriptorRegisterer(fd, 2));
				}
			}

		return fdRegisterer;
		}

	void writeLoop()
		{
		boost::shared_ptr<ScopedFileDescriptorRegisterer> fdRegisterer = getFdRegistrar(mFileDescriptor);

		if (!fdRegisterer)
			{
			disconnect();
			return;
			}


		try
			{
			while (true)
				{
				Nullable<std::string> dat = mQueuedItemsToWritePtr->get();

				if (dat)
					{
					uint32_t sz = dat->size();

					write(sz, mFileDescriptor);

					writeBytes(mFileDescriptor, &(*dat)[0], sz);
					}
				else
					//this is the clean shutdown case - just exit
					return;
				}
			}
		catch (ChannelDisconnected& )
			{
			disconnect();
			}
		catch (std::logic_error& e)
			{
			LOG_CRITICAL << "disconnecting socket channel due to exception: " << e.what();
			abort();
			}
		catch (...)
			{
			LOG_CRITICAL << "SocketChannel threw unknown exception. aborting";
			abort();
			}
		}

	static void readloopStatic(
					weak_ptr_type weakSocketPtr
					)
		{
		pointer_type socket = weakSocketPtr.lock();

		if (!socket)
			return;

		socket->readLoop();
		}

	void readLoop()
		{
		boost::shared_ptr<ScopedFileDescriptorRegisterer> fdRegisterer = getFdRegistrar(mFileDescriptor);

		if (!fdRegisterer)
			{
			disconnect();
			return;
			}


		try
			{
			while (true)
				{
				uint32_t msgSize = 0;
				read(msgSize, mFileDescriptor);

				std::string toWrite;

				if (msgSize < 1024*1024)
					{
					toWrite.resize(msgSize);

					readBytes(mFileDescriptor, &toWrite[0], toWrite.size());
					}
				else
					{
					std::ostringstream str;

					while (msgSize > 0)
						{
						std::string dat;
						dat.resize(msgSize > 1024*1024?1024*1024:msgSize);

						readBytes(mFileDescriptor, &dat[0], dat.size());
						str << dat;
						msgSize -= dat.size();
						}

					toWrite = str.str();
					}

				onMessage(toWrite);
				}
			}
		catch (ChannelDisconnected& e)
			{
			disconnect();
			}
		catch (std::logic_error& e)
			{
			LOG_CRITICAL << "disconnecting socket channel due to exception in onMessage: " << e.what();
			abort();
			}
		catch (...)
			{
			LOG_CRITICAL << "disconnecting socket channel due to unknown exception";
			abort();
			}
		}

private:
	PolymorphicSharedPtr<CallbackScheduler> mCallbackScheduler;

	static void defaultDisconnectHandler() {}

	boost::recursive_mutex mMutex;

	int32_t	mFileDescriptor;

	Ufora::thread::BsaThreadData mReadThread;

	Ufora::thread::BsaThreadData mWriteThread;

	string	mDescription;

	boost::shared_ptr<Queue<Nullable<std::string> > > mQueuedItemsToWritePtr;

	int64_t	mBytesWritten;

	bool mIsDisconnected;

	bool mThreadsStarted;

	boost::function1<void, std::string> mOnMessage;

	boost::function0<void> mOnDisconnected;

	bool mHandlersSet;

};


#endif

