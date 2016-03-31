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


const string OnDiskCompilerStore::INDEX_FILE_EXTENSION = ".idx";
const string OnDiskCompilerStore::DATA_FILE_EXTENSION = ".dat";
const string OnDiskCompilerStore::STORE_FILE_PREFIX = "CompilerStore";
const string OnDiskCompilerStore::MAP_FILE_PREFIX = "ClassMediatorToCFG";
const string OnDiskCompilerStore::MAP_FILE_EXTENSION = ".map";

void removeIfExists(const fs::path& file)
	{
	if (fs::exists(file))
		fs::remove(file);
	}

inline
Nullable<fs::path> getFileWithNewExtension(
		const fs::path& file,
		const string& currentExtension,
		const string& newExtension)
	{
	const string& fileStr = file.string();
	const string suffix = fileStr.substr(
			fileStr.size()- currentExtension.size(),
			currentExtension.size());
	if (suffix.compare(currentExtension))
		return null();

	string newFileStr =
				fileStr.substr(
						0,
						fileStr.size() - currentExtension.size()
						)
				+ newExtension;
	return null() << fs::path(newFileStr);
	}

Nullable<fs::path> OnDiskCompilerStore::getDataFileFromIndexFile(const fs::path& indexFile)
	{
	return getFileWithNewExtension(indexFile, INDEX_FILE_EXTENSION, DATA_FILE_EXTENSION);
	}

Nullable<fs::path> OnDiskCompilerStore::getIndexFileFromDataFile(const fs::path& dataFile)
	{
	return getFileWithNewExtension(dataFile, DATA_FILE_EXTENSION, INDEX_FILE_EXTENSION);
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

	if (mStoreFilesRead.find(file) != mStoreFilesRead.end())
		{
		LOG_ERROR << "File already loaded: " << file.string();
		return shared_ptr<vector<char> >();
		}

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

bool OnDiskCompilerStore::tryRebuildIndexFromData(
		const fs::path& rootDir,
		const fs::path& indexFile,
		const fs::path& dataFile)
	{
	// TODO: implement
	return false;
	}

bool OnDiskCompilerStore::initializeStoreIndex(const fs::path& rootDir, const fs::path& indexFile)
	{
	if (!fs::exists(rootDir / indexFile))
		return false;

	auto dataFile = getDataFileFromIndexFile(indexFile);
	if (!dataFile)
		{
		// Do *not* remove indexFile. It could be a useful non-index file.
		return false;
		}

	if (!fs::exists(rootDir / *dataFile))
		{
		LOG_WARN << "Removing index file '" << indexFile.string()
				<< "' because the corresponding data file could not be found.";
		removeIfExists(rootDir / indexFile);
		return false;
		}

	shared_ptr<vector<char> > dataBuffer = loadAndValidateFile(rootDir/indexFile);
	if (!dataBuffer)
		{
		bool res = tryRebuildIndexFromData(rootDir, indexFile, *dataFile);
		if (!res)
			{
			LOG_WARN << "Failed to load compiler cache index file: " << indexFile.string();

			removeIfExists(rootDir / indexFile);
			removeIfExists(rootDir / *dataFile);
			mStoreFilesRead.erase(*dataFile);
			}
		return res;
		}

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
			mLocationIndex.tryInsert(objId, *dataFile);
			}
		}
	return true;
	}

void OnDiskCompilerStore::initializeStoreIndex()
	{
	vector<fs::path> indexFiles;
	getFilesWithExtension(mBasePath, INDEX_FILE_EXTENSION, indexFiles);

	for (auto& indexFile: indexFiles)
		{
		initializeStoreIndex(mBasePath, indexFile);
		}
	}

bool OnDiskCompilerStore::initializeMap(const fs::path& rootDir, const fs::path& mapFile)
	{
	if (!fs::exists(rootDir / mapFile))
		return false;
	shared_ptr<vector<char> > dataBuffer = loadAndValidateFile(rootDir/mapFile);
	if (!dataBuffer)
		{
		LOG_WARN << "Failed to load compiler cache map file: " << mapFile.string();
		removeIfExists(rootDir / mapFile);
		return false;
		}

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
			CompilerMapKey key;
			deserializer.deserialize(key);
			ObjectIdentifier objId;
			deserializer.deserialize(objId);
			mMap[key] = objId;
			}
		}
	return true;
	}

bool OnDiskCompilerStore::initializeMap()
	{
	vector<fs::path> files;
	getFilesWithExtension(mBasePath, MAP_FILE_EXTENSION, files);
	bool atLeastOneSucceded = false;
	for (auto& file: files)
		atLeastOneSucceded |= initializeMap(mBasePath, file);

	return atLeastOneSucceded;
	}

fs::path OnDiskCompilerStore::getFreshMapFile()
	{
	static uint64_t index = 0;
	for (; true; ++index)
		{
		stringstream mapSS;
		mapSS << MAP_FILE_PREFIX << index << MAP_FILE_EXTENSION;
		string mapFileStr;
		mapSS >> mapFileStr;
		fs::path mapFile(mapFileStr);
		if (fs::exists(mBasePath / mapFile))
			continue;
		return mapFile;
		}
	}

pair<fs::path, fs::path> OnDiskCompilerStore::getFreshStoreFilePair()
	{
	static uint64_t index = 0;
	for(; true; ++index)
		{
		stringstream dataSS;
		dataSS << STORE_FILE_PREFIX << index << DATA_FILE_EXTENSION;
		string dataFileStr;
		dataSS >> dataFileStr;
		fs::path dataFile(dataFileStr);
		if (fs::exists(mBasePath / dataFile))
			continue;

		stringstream indexSS;
		indexSS << STORE_FILE_PREFIX << index << INDEX_FILE_EXTENSION;
		string indexFileStr;
		indexSS >> indexFileStr;
		fs::path indexFile(indexFileStr);
		if (fs::exists(mBasePath / indexFile))
			continue;

		return make_pair(dataFile, indexFile);
		}
	}

void OnDiskCompilerStore::cleanUpLocationIndex(const fs::path& problematicDataFile)
	{
	LOG_DEBUG << "Cleaning up Index from problematic data file: "
			<< problematicDataFile.string();
	mLocationIndex.dropValue(problematicDataFile);
	removeIfExists(mBasePath / problematicDataFile);
	mStoreFilesRead.erase(mBasePath / problematicDataFile);
	auto indexFile = getIndexFileFromDataFile(problematicDataFile);
	if (indexFile)
		removeIfExists(mBasePath / *indexFile);
	}

bool OnDiskCompilerStore::loadDataFromDisk(const fs::path& relativePathToFile)
	{
	fs::path absolutePathToFile = mBasePath / relativePathToFile;
	if (!fs::exists(absolutePathToFile) || !fs::is_regular_file(absolutePathToFile))
		{
		cleanUpLocationIndex(relativePathToFile);
		return false;
		}

	shared_ptr<vector<char> > dataBuffer = loadAndValidateFile(absolutePathToFile);
	if (!dataBuffer)
		{
		cleanUpLocationIndex(relativePathToFile);
		return false;
		}

	lassert(dataBuffer);
	char* dataPtr = &(*dataBuffer)[0];
	IMemProtocol protocol(dataPtr, dataBuffer->size());
	try
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
		for (int i = 0; i < entryCount; ++i)
			{
			ObjectIdentifier objId;
			MemoizableObject obj;
			deserializer.deserialize(objId);
			deserializer.deserialize(obj);
			mSavedObjectMap.insert(make_pair(objId, obj));
			}
		mPerformanceCounters.addDeserializationTime(curClock()-t0);

		auto memoizedRestoredObjects = deserializer.getRestoredObjectMap();
		if (memoizedRestoredObjects)
			mSavedObjectMap.insert(
					memoizedRestoredObjects->begin(),
					memoizedRestoredObjects->end());
		}
	catch (std::logic_error& e)
		{
		LOG_ERROR << e.what();
		return false;
		}
	return true;
	}

bool OnDiskCompilerStore::checksumAndStore(const NoncontiguousByteBlock& data, fs::path file)
	{
	ofstream ofs(file.string(), ios::out | ios::binary | ios::trunc);
	if (!ofs.is_open())
		{
		LOG_ERROR << "Failed to open file for writing: " << file.string();
		return false;
		}

	hash_type checksum = data.hash();

	ONoncontiguousByteBlockProtocol protocol;
		{
		OBinaryStream stream(protocol);
		CompilerCacheDuplicatingSerializer serializer(stream);
		serializer.serialize(checksum);
		}
	auto serializedChecksum = protocol.getData();
	if (!serializedChecksum)
		{
		LOG_ERROR << "Failed to serialize checksum";
		return false;
		}

	double t0 = curClock();
	ofs << *serializedChecksum;
	ofs << data;
	mPerformanceCounters.addDiskStoreTime(curClock()-t0);

	ofs.close();
	return true;
	}

template<class Key, class Value>
bool OnDiskCompilerStore::serializeAndStoreMap(
		const map<Key, Value>& map,
		const fs::path& file,
		bool justTheIndex)
	{
	ONoncontiguousByteBlockProtocol protocol;
		{
		OBinaryStream stream(protocol);
		CompilerCacheDuplicatingSerializer serializer(stream);
		uword_t entryCount = map.size();

		double t0 = curClock();
		serializer.serialize(entryCount);
		for(auto& pair: map)
			{
			serializer.serialize(pair.first);
			if (!justTheIndex)
				serializer.serialize(pair.second);
			}
		mPerformanceCounters.addSerializationTime(curClock()-t0);
		}
	auto serializedData = protocol.getData();
	if (!serializedData)
		{
		LOG_ERROR << "Failed to serialize Compiler-Cache index";
		return false;
		}
	return checksumAndStore(*serializedData, file);
	}

bool OnDiskCompilerStore::flushToDisk()
	{
	bool noErrorSoFar = true;

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

			for (auto& pair: mUnsavedObjectMap)
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
		if (!serializedData)
			{
			LOG_ERROR << "Failed to serialize Compiler-Cache data";
			return false;
			}
		noErrorSoFar &= checksumAndStore(*serializedData, dataFile);

		}

	if (storedObjects)
		noErrorSoFar &= serializeAndStoreMap(*storedObjects, indexFile, true);

	// write .map file
	fs::path newMapFile = getFreshMapFile();
	bool res = serializeAndStoreMap(mMap, mBasePath / newMapFile);
	if (res)
		{ // find and delete all other .map files
		vector<fs::path> mapFiles;
		getFilesWithExtension(mBasePath, MAP_FILE_EXTENSION, mapFiles);
		for (auto& mapFile: mapFiles)
			if (mapFile != newMapFile)
				removeIfExists(mBasePath / mapFile);
		}
	noErrorSoFar &= res;
	return noErrorSoFar;
	}

OnDiskCompilerStore::OnDiskCompilerStore(fs::path inBasePath) :
		mBasePath(inBasePath)
	{
	if (!fs::exists(mBasePath))
		fs::create_directories(mBasePath);

	initializeStoreIndex();
	initializeMap();

	validateIndex();
	}

bool OnDiskCompilerStore::containsOnDisk(const ObjectIdentifier& inKey) const
	{
	if (mSavedObjectMap.find(inKey) != mSavedObjectMap.end() ||
			mLocationIndex.hasKey(inKey))
		return true;
	else
		return false;
	}

void OnDiskCompilerStore::validateIndex()
	{
	std::set<fs::path> valuesToDrop;
	for (auto term : mLocationIndex.getValueToKeys())
		{
		if (!fs::exists(mBasePath / term.first))
			valuesToDrop.insert(term.first);
		}
	for (auto value : valuesToDrop)
		{
		mLocationIndex.dropValue(value);
		LOG_WARN << "Dropping Compiler Store object IDs to file '"
				<< value.string() << "'";
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

	auto file = mLocationIndex.tryGetValue(inKey);
	if (!file)
		return null();

	if (!loadDataFromDisk(*file))
		{
		LOG_WARN << "Unable to load Compiler Cache data from file '"
				<< (mBasePath / *file).string() << "'";
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
		auto& existingValue =(*findIt).second.extract<T>();
		if(existingValue == inValue)
			{
			inSavedMap = true;
			// don't return, proceed to check if (key, value) pair exists on disk as well
			}
		else
			{
			// found key that maps to different values
			LOG_ERROR << "Compiler-Cache key maps to different values:\n"
					<< "Key in Compiler-Cache: " << prettyPrintString(inKey)
					<< "Value in Compiler-Cache:\n" << prettyPrintString(existingValue)
					<< "Value to be inserted (which has identical key):\n"
					<< prettyPrintString(inValue)
					;
			lassert(false);
			}
		}

	if (mLocationIndex.hasKey(inKey))
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

	auto objIt = mMap.find(inKey);
	if (objIt == mMap.end())
		{
		return null();
		}

	const ObjectIdentifier objId = (*objIt).second;

	auto res = lookup<ControlFlowGraph>(objId);
	return res;
	}


void OnDiskCompilerStore::set(const CompilerMapKey& inKey, const ControlFlowGraph& inCFG)
	{
	ObjectIdentifier objId(makeObjectIdentifier(inCFG));

	mMap.insert(make_pair(inKey, objId));
	store(objId, inCFG);

	}
