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
#include "ChecksummedFile.hpp"
#include "OpenFiles.hpp"
#include "../../../core/Logging.hpp"
#include "../../../core/Clock.hpp"

namespace SharedState {

OpenFiles::OpenFiles(uint32_t maxOpenFiles) :
		mIsShutdown(false),
		mMaxOpenFiles(maxOpenFiles),
		mFileAccessCount(0)
	{
	}

OpenFiles::~OpenFiles()
	{
	if (!mIsShutdown)
		{
		LOG_WARN << "OpenFiles has not been shutdown prior to destruction";
		shutdown();
		}
	lassert(!mFlushLoopThread.joinable());
	lassert(mOpenFiles.size() == 0);
	}

bool OpenFiles::readFileAsStringVector(const std::string& path, std::vector<std::string>& out) const
    {
	boost::recursive_mutex::scoped_lock lock(mMutex);
    return ChecksummedFile::readAllToVector(path, out);
    }

void OpenFiles::append(const std::string& path, const std::string& contents)
	{
	boost::recursive_mutex::scoped_lock lock(mMutex);
	if (mIsShutdown)
		{
		LOG_ERROR << "Attempting to append to file " << path << " after shutdown. Content is not written!";
		return;
		}

	writer_ptr_type writer = getFile(path);
	if (!writer)
		{
		writer = openFile(path);
		}

	writer->writeString(contents);
	recordFileAccess(path);
	}

OpenFiles::writer_ptr_type OpenFiles::openFile(const std::string& path)
	{
	LOG_INFO << "opening file " << path << ". total filecount = " << mOpenFiles.size();

	closeFilesIfNecessary();
	try {
		OpenFiles::writer_ptr_type writer = OpenFiles::writer_ptr_type(new writer_type(path));
		lassert(writer->written() == 0);
		mOpenFiles[path] = writer;
		return writer;
		}
	catch(std::logic_error& e)
		{
		LOG_WARN << "Failed to open file: " << path << ". Error: " << e.what();
		throw;
		}
	}


uint64_t OpenFiles::written(const std::string& path) const
	{
	boost::recursive_mutex::scoped_lock lock(mMutex);
	const_writer_ptr_type writer = getFile(path);
	return writer ? writer->written() : 0;
	}

void OpenFiles::flush(const std::string& path)
	{
	boost::recursive_mutex::scoped_lock lock(mMutex);
	writer_ptr_type writer = getFile(path);
	if (writer)
		writer->flush();
	}

void OpenFiles::closeFile(const std::string& path)
	{
	auto it = mOpenFiles.find(path);
	if(it != mOpenFiles.end())
		mOpenFiles.erase(it);
	}


void OpenFiles::closeAFile()
	{
	boost::recursive_mutex::scoped_lock lock(mMutex);
	lassert(mFileAccesses.size());

	uint64_t lowestFileIx = mFileAccesses.lowestValue();
	std::string toClose = getFileNameFromAccessId(lowestFileIx);

	LOG_INFO << "closing file " << toClose
		<< " because we have too many open files (" << mOpenFiles.size() << ")";

	mOpenFiles.erase(toClose);
	mFileAccesses.drop(toClose);
	}


void OpenFiles::shutdown()
	{
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);
		mIsShutdown = true;
		mShutdownCondition.notify_all();
		}

	if (mFlushLoopThread.joinable())
		{
		LOG_INFO << "flush loop joining";
		mFlushLoopThread.join();
		}

	while (mOpenFiles.size())
		closeAFile();
	}

void OpenFiles::recordFileAccess(const std::string& filename)
	{
	mFileAccessCount++;
	mFileAccesses.set(filename, mFileAccessCount);

	if (!isFlushLoopRunning() && !mIsShutdown)
		{
		mFlushLoopThread = boost::thread(boost::bind(&OpenFiles::flushLoop, this));
		}
	}

void OpenFiles::closeFilesIfNecessary()
	{
	while (mOpenFiles.size() >= mMaxOpenFiles)
		closeAFile();
	}

std::string OpenFiles::getFileNameFromAccessId(uint64_t accessId) const
	{
	auto fileNames = mFileAccesses.getKeys(accessId);
	if (fileNames.size() != 1)
		{
		LOG_CRITICAL << "Expecting exactly one file to exist at file access index " << accessId
			<< ". Got " << fileNames.size() << ". Aborting.";
		fflush(stdout);
		fflush(stderr);
		abort();
		}

	return *fileNames.begin();
	}

bool OpenFiles::isFlushLoopRunning() const
	{
	return mFlushLoopThread.joinable();
	}

void OpenFiles::flushLoop()
	{
	LOG_INFO << "Entering flush loop";
	uint64_t lastSeenAccess = 0;
	uint64_t currentAccess = 0;
	bool shuttingDown = false;

	while (!shuttingDown)
		{
		if (currentAccess > lastSeenAccess)
			{
			flushFiles(lastSeenAccess+1, currentAccess);
			lastSeenAccess = currentAccess;
			}

		boost::recursive_mutex::scoped_lock lock(mMutex);
		mShutdownCondition.timed_wait(lock, boost::posix_time::milliseconds(1000));
		shuttingDown = mIsShutdown;
		currentAccess = mFileAccessCount;
		}
	LOG_INFO << "Exiting flush loop";
	}

void OpenFiles::flushFiles(uint64_t fromAccess, uint64_t toAccess)
	{
	LOG_DEBUG << "flushing from " << fromAccess << " to " << toAccess;
	std::vector<writer_ptr_type> accessedFiles;
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);
		for (uint64_t i = fromAccess; i <= toAccess; ++i)
			{
			if (mFileAccesses.hasValue(i))
				{
				std::string filename = getFileNameFromAccessId(i);
				auto it = mOpenFiles.find(filename);
				if (it != mOpenFiles.end())
					{
					accessedFiles.push_back(it->second);
					}
				}
			}
		}

	for (writer_ptr_type fileWriter: accessedFiles)
		{
		if (fileWriter->isDirty())
			{
			fileWriter->flush();
			}
		}
	}


OpenFiles::writer_ptr_type OpenFiles::getFile(const std::string& filename)
	{
	return boost::const_pointer_cast<OpenFiles::writer_type>(
			static_cast<const OpenFiles&>(*this).getFile(filename)
			);
	}

OpenFiles::const_writer_ptr_type OpenFiles::getFile(const std::string& filename) const
	{
	auto iter = mOpenFiles.find(filename);
	if (iter != mOpenFiles.end())
		return iter->second;

	return OpenFiles::writer_ptr_type();

	}

}

