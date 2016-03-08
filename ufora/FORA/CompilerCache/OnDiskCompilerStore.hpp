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
#pragma once

#include "CompilerMapKey.hppml"
#include "MemoizableObject.hppml"
#include "ObjectIdentifier.hppml"
#include "PerformanceCounters.hpp"
#include "../../core/containers/MapWithIndex.hpp"

#define BOOST_FILESYSTEM_NO_DEPRECATED
#include <boost/filesystem.hpp>
#include <unordered_map>

namespace fs = ::boost::filesystem;

class NoncontiguousByteBlock;
class ObjectIdentifier;


class OnDiskCompilerStore {
public:
	OnDiskCompilerStore(const fs::path inBasePath);

	Nullable<ControlFlowGraph> get(const CompilerMapKey& inKey);
	void set(const CompilerMapKey& inKey, const ControlFlowGraph& inCFG);

	// Object Store Operations
	template<class T>
	Nullable<T> lookup(const ObjectIdentifier& inKey);

	template<class T>
	Nullable<T> lookupInMemory(const ObjectIdentifier& inKey) const;

	template<class T>
	void store(const ObjectIdentifier& inKey, const T& inVal);

	bool containsOnDisk(const ObjectIdentifier& inKey) const;

	std::string getPerformanceStats() { return mPerformanceCounters.printStats(); }

	bool flushToDisk();

private:
	pair<fs::path, fs::path> getFreshStoreFilePair();

	bool loadDataFromDisk(const fs::path& file);

	shared_ptr<vector<char> > loadAndValidateFile(const fs::path& file);

	bool checksumAndStore(const NoncontiguousByteBlock& data, fs::path file);

	void initializeStoreIndexes();

	bool initializeStoreIndex(const fs::path& rootDir, const fs::path& file);

	bool tryRebuildIndexFromData(
			const fs::path& rootDir,
			const fs::path& indexFile,
			const fs::path& dataFile);

	void validateIndex();

	template<class T>
	bool saveIndexToDisk(const fs::path& file, const T& index) const;

	template<class T>
	bool initializeIndex(const fs::path& file, T& index);

	void cleanUpLocationIndex(const fs::path& problematicDataFile);

private:
	// We currently rely on the lock held by the CompilerCache Object which holds
	// this CompilerStore
//	boost::recursive_mutex mMutex;

	// Paths
	const fs::path mBasePath;
	fs::path mMapFile;

	// Maps. FIXME: switch to using hash-maps
	// \brief (CompilerMapKey -> ControlFlowGraph_ObjectIdentifier) map
	map<CompilerMapKey, ObjectIdentifier> mMap; //TODO: make unordered_map (missing serialization)

	unordered_map<ObjectIdentifier, MemoizableObject> mSavedObjectMap;

	unordered_map<ObjectIdentifier, MemoizableObject> mUnsavedObjectMap;

	/// \brief Maps Object Identifiers to relative paths (relative to mBasePath)
	MapWithIndex<ObjectIdentifier, fs::path> mLocationIndex;

	/// \brief This set allows us to detect and break recursive load cycles, which shouldn't exist.
	std::set<fs::path> mStoreFilesRead;

	mutable PerformanceCounters mPerformanceCounters;

	////////////////////////////////////////////////////////////
	// CONSTANTS
	static const string INDEX_EXTENSION;
	static const string DATA_EXTENSION;
	static const string STORE_FILE_PREFIX;

public:
	static Nullable<fs::path> getDataFileFromIndexFile(const fs::path& indexFile);
	static Nullable<fs::path> getIndexFileFromDataFile(const fs::path& indexFile);
};
