/***************************************************************************
   Copyright 2015-2016 Ufora Inc.

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
#include "CompilerCacheSerializer.hpp"
#include "MemoizableObject.hppml"
#include "OnDiskCompilerStore.hpp"
#include "../Core/ClassMediator.hppml"
#include "../Core/MemoryPool.hpp"
#include "../../core/Clock.hpp"
#include "../../core/Memory.hpp"
#include "../../core/serialization/IFileDescriptorProtocol.hpp"
#include "../../core/serialization/INoncontiguousByteBlockProtocol.hpp"
#include "../../core/serialization/OFileDescriptorProtocol.hpp"
#include "../../core/serialization/ONoncontiguousByteBlockProtocol.hpp"
#include <fstream>
#include <fcntl.h>


const string OnDiskCompilerStore::INDEX_EXTENSION = ".idx";
const string OnDiskCompilerStore::DATA_EXTENSION = ".dat";
const string OnDiskCompilerStore::STORE_FILE_PREFIX = "CompilerStore";

template<class T>
void OnDiskCompilerStore::saveIndexToDisk(const fs::path& file, const T& index) const
	{
	double t0 = curClock();
	LOG_DEBUG << "Trying to save index to Disk";

	if (fs::exists(file))
		fs::remove(file);
	lassert_dump(!fs::exists(file), file);

	int fd = open(file.string().c_str(),  O_CREAT| O_WRONLY, S_IRUSR|S_IWUSR);
	lassert_dump(fd != -1, "failed to open " << file.string() << ": " << strerror(errno));
		{
		OFileDescriptorProtocol protocol(
			fd,
			1,
			1024 * 1024 * 20,
			OFileDescriptorProtocol::CloseOnDestroy::True
			);

			{
			OBinaryStream stream(protocol);

			CompilerCacheDuplicatingSerializer serializer(stream);

			serializer.serialize(index);
			}

		LOG_DEBUG << "Disk cache index stored: "
			<< protocol.position() /*/ 1024 / 1024.0 << " MB. " */ << " bytes. "
			<< " path = " << file.string()
			;

		}
		mPerformanceCounters.addDiskStoreTime(curClock() - t0);
	}

template<class T>
void OnDiskCompilerStore::initializeIndex(const fs::path& file, T& index)
	{
	LOG_DEBUG << "Trying to initialize index from Disk";
	// open file if present.
	if (!fs::exists(file))
		{
		LOG_DEBUG << "Index File not found: " << file.string();
		return;
		}

	int fd = open(file.string().c_str(), O_RDONLY, S_IRWXU);
	lassert_dump(fd != -1, "failed to open " << file.string() << ": " << strerror(errno));

	IFileDescriptorProtocol protocol(
		fd,
		1,
		20 * 1024 * 1024,
		IFileDescriptorProtocol::CloseOnDestroy::True
		);
		{
		IBinaryStream stream(protocol);

		CompilerCacheDuplicatingDeserializer deserializer(
				stream,
				MemoryPool::getFreeStorePool(),
				PolymorphicSharedPtr<VectorDataMemoryManager>()
				);

		double t0 = curClock();
		deserializer.deserialize(index);
		double time = curClock() - t0;
		mPerformanceCounters.addDiskLookupTime(time);
		mPerformanceCounters.addDeserializationTime(time);
		}

	LOG_DEBUG << "Initialized index: size=" << index.size();
	}

template<class T>
void logDebugMap(T& map) {
	LOG_DEBUG << "Printing Index:";
	for(auto term: map)
		{
		LOG_DEBUG << prettyPrintString(term.first)
				<< " -> " << prettyPrintString(term.second);
		}
}
shared_ptr<vector<char> > OnDiskCompilerStore::loadAndValidateFile(const fs::path& file)
	{
	if (!fs::exists(file) || !fs::is_regular_file(file))
		return shared_ptr<vector<char> >();

	lassert_dump(
			mStoreFilesRead.find(file) == mStoreFilesRead.end(),
			"File already loaded: " << file.string()
			);

	ifstream fin(file.string(), ios::in | ios::binary);
	if (!fin.is_open())
		return shared_ptr<vector<char> >();

	hash_type storedChecksum;
	constexpr auto checksumSize = sizeof(hash_type);
	vector<char> checksumBuffer(checksumSize);
	char* checksumPtr = &checksumBuffer[0];
	fin.read(checksumPtr, checksumSize);
	if (!fin)
		{
		fin.close();
		return shared_ptr<vector<char> >();
		}

	IMemProtocol protocol(checksumPtr, checksumBuffer.size());
		{
		IBinaryStream stream(protocol);
		CompilerCacheDuplicatingDeserializer deserializer(
				stream,
				MemoryPool::getFreeStorePool(),
				PolymorphicSharedPtr<VectorDataMemoryManager>()
				);
		deserializer.deserialize(storedChecksum);
		}

	const uword_t bufferSize = fs::file_size(file) - checksumSize;
	shared_ptr<vector<char> > result(new vector<char>(bufferSize));
	char* bufPtr = &(*result)[0];

	// 2. read rest
	double t0 = curClock();
	fin.read(bufPtr, bufferSize);
	mPerformanceCounters.addDiskLookupTime(curClock()-t0);
	if (!fin)
		{
		fin.close();
		return shared_ptr<vector<char> >();
		}
	// else
	fin.close();

	hash_type computedChecksum = hashValue(*result);

	if (computedChecksum != storedChecksum)
		{

		return shared_ptr<vector<char> >();
		}

	mStoreFilesRead.insert(file);
	return result;
	}

void getFilesWithExtension(const fs::path& rootDir, const string& ext, vector<fs::path>& outFiles)
	{
	if(!fs::exists(rootDir) || !fs::is_directory(rootDir)) return;

	fs::recursive_directory_iterator it(rootDir);
	fs::recursive_directory_iterator endit;

	while(it != endit)
		{
		if(fs::is_regular_file(*it)  &&  it->path().extension() == ext)
			outFiles.push_back(it->path().filename());
		++it;

		}
	}

void OnDiskCompilerStore::initializeStoreIndex(const fs::path& rootDir, const fs::path& indexFile)
	{
	shared_ptr<vector<char> > dataBuffer = loadAndValidateFile(rootDir/indexFile);
	lassert(dataBuffer);

	const string& indexFileStr = indexFile.string();
	string dataFileStr =
			indexFileStr.substr(
					0,
					indexFileStr.size() - INDEX_EXTENSION.size()
					)
			+ DATA_EXTENSION;
	OnDiskLocation loc(dataFileStr, 0);
	char* dataPtr = &(*dataBuffer)[0];
	IMemProtocol protocol(dataPtr, dataBuffer->size());

		{
		IBinaryStream stream(protocol);
		CompilerCacheDuplicatingDeserializer deserializer(
				stream,
				MemoryPool::getFreeStorePool(),
				PolymorphicSharedPtr<VectorDataMemoryManager>()
				);
		uword_t entryCount = 0;
		deserializer.deserialize(entryCount);
		for(int i = 0; i < entryCount; ++i)
			{
			ObjectIdentifier objId;
			deserializer.deserialize(objId);
			mLocationIndex.insert(make_pair(objId, loc));
			}
		}
	}

void OnDiskCompilerStore::initializeStoreIndexes()
	{
	vector<fs::path> indexFiles;
	getFilesWithExtension(mBasePath, INDEX_EXTENSION, indexFiles);

	for (auto& indexFile: indexFiles)
		{
		initializeStoreIndex(mBasePath, indexFile);
		}
	}

pair<fs::path, fs::path> OnDiskCompilerStore::getFreshStoreFilePair()
	{
	static uint64_t index = 0;
	for(; true; ++index)
		{
		stringstream dataSS;
		dataSS << STORE_FILE_PREFIX << index << DATA_EXTENSION;
		string dataFileStr;
		dataSS >> dataFileStr;
		fs::path dataFile(dataFileStr);
		if (fs::exists(mBasePath / dataFile))
			continue;

		stringstream indexSS;
		indexSS << STORE_FILE_PREFIX << index << INDEX_EXTENSION;
		string indexFileStr;
		indexSS >> indexFileStr;
		fs::path indexFile(indexFileStr);
		if (fs::exists(mBasePath / indexFile))
			continue;

		++index;
		return make_pair(dataFile, indexFile);
		}
	}

bool OnDiskCompilerStore::loadDataFromDisk(fs::path file)
	{
	if (!fs::exists(file) || !fs::is_regular_file(file))
		return false;
	shared_ptr<vector<char> > dataBuffer = loadAndValidateFile(file);
	lassert(dataBuffer);

	char* dataPtr = &(*dataBuffer)[0];
	IMemProtocol protocol(dataPtr, dataBuffer->size());
		{
		IBinaryStream stream(protocol);
		CompilerCacheMemoizingBufferedDeserializer deserializer(
				stream,
				MemoryPool::getFreeStorePool(),
				PolymorphicSharedPtr<VectorDataMemoryManager>(),
				*this
				);

		uword_t entryCount;
		double t0 = curClock();
		deserializer.deserialize(entryCount);
		LOG_DEBUG_SCOPED("Deserialization") << "gonna deserialize " << entryCount << " entries.";
		for (int i = 0; i < entryCount; ++i)
			{
			ObjectIdentifier objId;
			MemoizableObject obj;
			deserializer.deserialize(objId);
			LOG_DEBUG_SCOPED("Deserialization") << "gonna deserialize " << prettyPrintString(objId);
			deserializer.deserialize(obj);
			LOG_DEBUG_SCOPED("Deserialization") << "1 entry deserialized: " << prettyPrintString(objId);
			mSavedObjectMap.insert(make_pair(objId, obj)); // FIXME
			}
		mPerformanceCounters.addDeserializationTime(curClock()-t0);

		auto memoizedRestoredObjects = deserializer.getRestoredObjectMap();
		if (memoizedRestoredObjects)
			mSavedObjectMap.insert(
					memoizedRestoredObjects->begin(),
					memoizedRestoredObjects->end());
	}

	return true;
	}

void OnDiskCompilerStore::checksumAndStore(const NoncontiguousByteBlock& data, fs::path file)
	{
	ofstream ofs(file.string(), ios::out | ios::binary | ios::trunc);
	lassert(ofs.is_open());

	hash_type checksum = data.hash();

	ONoncontiguousByteBlockProtocol protocol;
		{
		OBinaryStream stream(protocol);
		CompilerCacheDuplicatingSerializer serializer(stream);
		serializer.serialize(checksum);
		}
	auto serializedChecksum = protocol.getData();
	lassert(serializedChecksum);

	double t0 = curClock();
	ofs << *serializedChecksum;
	ofs << data;
	mPerformanceCounters.addDiskStoreTime(curClock()-t0);

	ofs.close();
	}

void OnDiskCompilerStore::flushToDisk()
	{
	auto pair = getFreshStoreFilePair();
	const fs::path& dataFile = mBasePath / pair.first;
	const fs::path& indexFile = mBasePath / pair.second;

	// serialize mUnsavedObjectMap
	shared_ptr<map<ObjectIdentifier, MemoizableObject> > storedObjects;

		{
		ONoncontiguousByteBlockProtocol protocol;

			{
			OBinaryStream stream(protocol);
			CompilerCacheMemoizingBufferedSerializer serializer(stream, *this);

			double t0 = curClock();
			serializer.serialize(mUnsavedObjectMap.size());

			for (auto pair: mUnsavedObjectMap)
				{
				const ObjectIdentifier& curId = pair.first;
				const MemoizableObject& curObj = pair.second;
				serializer.serialize(curId);
				serializer.serialize(curObj);
				}
			double time = curClock() - t0;
			mPerformanceCounters.addSerializationTime(time);
			mUnsavedObjectMap.clear();

			storedObjects = serializer.getStoredObjectMap();
			if (storedObjects)
				{
				mSavedObjectMap.insert(storedObjects->begin(), storedObjects->end());
				}
			}

		// write .dat file
		auto serializedData = protocol.getData();
		lassert(serializedData);
		checksumAndStore(*serializedData, dataFile);

		}

		{ // write .idx file
		ONoncontiguousByteBlockProtocol protocol;
			{
			OBinaryStream stream(protocol);
			CompilerCacheDuplicatingSerializer serializer(stream);
			lassert(storedObjects);
			uword_t entryCount = storedObjects->size();

			double t0 = curClock();
			serializer.serialize(entryCount);
			for(auto pair: *storedObjects)
				{
				const ObjectIdentifier& objId = pair.first;
				serializer.serialize(objId);
				}
			mPerformanceCounters.addSerializationTime(curClock()-t0);
			}
		auto serializedData = protocol.getData();
		lassert(serializedData);
		checksumAndStore(*serializedData, indexFile);
		}

	saveIndexToDisk(mMapFile, mMap);
	}

OnDiskCompilerStore::OnDiskCompilerStore(fs::path inBasePath) :
		mBasePath(inBasePath)
	{
	if (!fs::exists(mBasePath))
		fs::create_directories(mBasePath);

	mMapFile = mBasePath / "CmToCfgMap.map";

	initializeStoreIndexes();
//	logDebugMap(mLocationIndex);
	initializeIndex(mMapFile, mMap);
//	logDebugMap(mMap);

	validateIndex();

	LOG_DEBUG_SCOPED("CompilerCachePerf") <<
			mPerformanceCounters.printStats();

	}

bool OnDiskCompilerStore::containsOnDisk(const ObjectIdentifier& inKey) const
	{
	if (mSavedObjectMap.find(inKey) != mSavedObjectMap.end() ||
			mLocationIndex.find(inKey) != mLocationIndex.end())
		return true;
	else
		return false;
	}

void OnDiskCompilerStore::validateIndex()
	{
	map<fs::path, uintmax_t> fileSizeMap;
	for(auto idxIt = mLocationIndex.begin(); idxIt != mLocationIndex.end();)
		{
		auto& term = *idxIt;
		const fs::path file(mBasePath / term.second.filePath());

		uintmax_t size = 0;
		auto it = fileSizeMap.find(file);
		if (it == fileSizeMap.end())
			{
			if (fs::exists(file))
				size = fs::file_size(file);
			else
				size = 0;
			auto res = fileSizeMap.insert(make_pair(file, size));
			lassert(res.second==true)
			}
		else
			{
			size = (*it).second;
			}

		if (term.second.fileOffset() >= size)
			{
			LOG_WARN << "Dropping Compiler Store Index pair: ("
					<< prettyPrintString(term.first) << ") -> ("
					<< prettyPrintString(term.second) << ")"
					;
			idxIt = mLocationIndex.erase(idxIt);
			}
		else
			{
			++idxIt;
			}
		}
	}

template<class T>
Nullable<T> OnDiskCompilerStore::lookupInMemory(const ObjectIdentifier& inKey) const
	{
	mPerformanceCounters.incrMemLookups();
	auto it = mSavedObjectMap.find(inKey);
	if (it != mSavedObjectMap.end())
		return null() << (*it).second.extract<T>();

	it = mUnsavedObjectMap.find(inKey);
	if (it != mUnsavedObjectMap.end())
		return null() << (*it).second.extract<T>();

	return null();
	}

template<class T>
Nullable<T> OnDiskCompilerStore::lookup(const ObjectIdentifier& inKey)
	{
	auto res = lookupInMemory<T>(inKey);
	if (res)
		return res;

	auto locIt = mLocationIndex.find(inKey);
	if (locIt == mLocationIndex.end())
		return null();

	fs::path file((*locIt).second.filePath());
	if (!loadDataFromDisk(mBasePath / file))
		{
		LOG_WARN << "Unable to load Compiler Cache data from file '"
				<< (mBasePath/file).string() << "'";
		return null();
		}

	res = lookupInMemory<T>(inKey);
	return res;
	}

template
Nullable<Expression> OnDiskCompilerStore::lookup<Expression>(const ObjectIdentifier& inKey);

template
Nullable<Type> OnDiskCompilerStore::lookup<Type>(const ObjectIdentifier& inKey);

template
Nullable<JOV> OnDiskCompilerStore::lookup<JOV>(const ObjectIdentifier& inKey);


template<class T>
void OnDiskCompilerStore::store(const ObjectIdentifier& inKey, const T& inValue)
	{
	auto findIt = mSavedObjectMap.find(inKey);
	bool inSavedMap = false;
	if (findIt != mSavedObjectMap.end())
		{
		lassert((*findIt).second.extract<T>() == inValue);
		inSavedMap = true;
		// don't return, proceed to check if (key, value) pair exists on disk as well
		}

	if (mLocationIndex.find(inKey) != mLocationIndex.end())
		{
		if (!inSavedMap)
			mSavedObjectMap.insert(
					make_pair(inKey, MemoizableObject::makeMemoizableObject(inValue))
					);
		return; // already exists // TODO: perhaps check that the location is valid
		}
	auto value = make_pair(inKey, MemoizableObject::makeMemoizableObject(inValue));
	auto insRes = mUnsavedObjectMap.insert(value);
	// TEMP SOLUTION TO FLUSHING
	if(mUnsavedObjectMap.size() > 5)
		flushToDisk();
	}

template
void OnDiskCompilerStore::store<MemoizableObject>(const ObjectIdentifier& inKey, const MemoizableObject& inValue);


Nullable<ControlFlowGraph> OnDiskCompilerStore::get(const CompilerMapKey& inKey)
	{
	ControlFlowGraph tr;
//	LOG_DEBUG << "CompilerStore::get " << inKey;

	auto objIt = mMap.find(inKey);
	if (objIt == mMap.end())
		{
		LOG_DEBUG << "key not found in compiler cache MAP: " << prettyPrintString(inKey);
		return null();
		}

	const ObjectIdentifier objId = (*objIt).second;

	auto res = lookup<ControlFlowGraph>(objId);
	return res;
	}


void OnDiskCompilerStore::set(const CompilerMapKey& inKey, const ControlFlowGraph& inCFG)
	{
//	LOG_DEBUG << "CompilerStore::set " << inKey;
	ObjectIdentifier objId(makeObjectIdentifier(inCFG));

	mMap.insert(make_pair(inKey, objId));
	store(objId, inCFG);

	LOG_DEBUG_SCOPED("CompilerCachePerf") <<
			mPerformanceCounters.printStats();

	}
