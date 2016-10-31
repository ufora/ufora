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

#include <unordered_map>
#include <boost/enable_shared_from_this.hpp>
#include "../../../core/containers/MapWithIndex.hpp"
#include <boost/thread.hpp>

namespace ChecksummedFile {
	class ChecksummedWriter;
};


namespace SharedState {

class OpenFilesInterface : public boost::enable_shared_from_this<OpenFilesInterface> {
public:
	virtual ~OpenFilesInterface() {};

	virtual void append(const std::string& path, const std::string& contents) = 0;

	virtual uint64_t written(const std::string& path) const = 0;

	virtual void flush(const std::string& path) = 0;

	virtual void shutdown() = 0;

	virtual void closeFile(const std::string& path) = 0;

	virtual bool readFileAsStringVector(const std::string& path,
										std::vector<std::string>& out) const = 0;
};


class OpenFiles : public OpenFilesInterface {
public:
	typedef ChecksummedFile::ChecksummedWriter writer_type;
	typedef boost::shared_ptr<writer_type> writer_ptr_type;
	typedef boost::shared_ptr<const writer_type> const_writer_ptr_type;

	OpenFiles(uint32_t);

	virtual ~OpenFiles();

	// disable copy sematics
	OpenFiles(const OpenFiles&) = delete;
	OpenFiles operator=(const OpenFiles&) = delete;

	virtual void append(const std::string& path, const std::string& contents);

	virtual uint64_t written(const std::string& path) const;

	virtual void flush(const std::string& path);

	virtual void shutdown();

	virtual void closeFile(const std::string& path);

	virtual bool readFileAsStringVector(const std::string& path,
										std::vector<std::string>& out) const;

private:
	bool isFlushLoopRunning() const;
	void flushLoop();
	void flushFiles(uint64_t fromAccess, uint64_t toAccess);

	void recordFileAccess(const std::string& filename);
	void closeFilesIfNecessary();

	std::string getFileNameFromAccessId(uint64_t accessId) const;

	writer_ptr_type getFile(const std::string& filename);
	const_writer_ptr_type getFile(const std::string& filename) const;

	writer_ptr_type openFile(const std::string& path);

	void closeAFile();

	mutable boost::recursive_mutex mMutex;
	boost::thread mFlushLoopThread;
	boost::condition_variable_any mShutdownCondition;
	bool mIsShutdown;

	std::unordered_map<std::string, writer_ptr_type> mOpenFiles;

	uint32_t mMaxOpenFiles;

	uint64_t mFileAccessCount;

	MapWithIndex<std::string, uint64_t> mFileAccesses;
};

}

