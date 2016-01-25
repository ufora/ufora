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
#include "SharedState.py.hpp"
#include "KeyType.hppml"
#include "KeyspaceCache.hppml"
#include <stdint.h>
#include <boost/python.hpp>
#include <boost/function.hpp>
#include "Storage/LogFileSerialization.hpp"
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"


class KeyspaceCacheWrapper {
public:
	static boost::shared_ptr<KeyspaceCache> newKeyspaceCache(
			const KeyRange& keyrange, boost::python::object inStorage
			)

		{
		PolymorphicSharedPtr<KeyspaceStorage> storage;
		boost::python::extract<PolymorphicSharedPtr<KeyspaceStorage> > extractor(inStorage);
		if(extractor.check())
			storage = extractor();
		return boost::shared_ptr<KeyspaceCache>(new KeyspaceCache(keyrange, storage));
		}

	static void newMinimumId(boost::shared_ptr<KeyspaceCache> inCache, EventIDType minId)
		{
		inCache->newMinimumId(minId);
		}

	static void addEvent(boost::shared_ptr<KeyspaceCache> inCache, const PartialEvent& event)
		{
		inCache->addEvent(event);
		}

	static void exportPythonInterface()
		{
		using namespace boost::python;
			
		class_<boost::shared_ptr<KeyspaceCache> >("KeyspaceCache")
			.def("newMinimumId", &newMinimumId)
			.def("addEvent", &addEvent)

			;
		def("KeyspaceCache", &newKeyspaceCache);
		}
};


namespace {

using namespace SharedState;
class OpenBinarySerializers : public OpenSerializers { 
	// implementation of OpenSerializers interface without JsonMemo
	// to aid in testing
public:
	typedef boost::shared_ptr<SerializedObjectStream<BinaryStreamSerializer > > serializer_ptr_type;
    void serializeLogEntryForPath(
			const std::string& path, 
			const LogEntry& inLog, 
			std::string& outSerialized)
        {
        serializeForPath(path, inLog, outSerialized);
        }

	std::string serializeStateForPath(
            const std::string& path, 
            const map<SharedState::Key, SharedState::KeyState>& inState)
        {
		// no need to keep track of this it will not be kept open.
		serializer_ptr_type serializer = 
			serializer_ptr_type(new SerializedObjectStream<BinaryStreamSerializer>());
		return serializer->serialize(inState);
        }

	void finishedWithSerializer(const std::string& path)
		{
		auto it = mSerializers.find(path);
		if(it != mSerializers.end())
			mSerializers.erase(it);
		}
    bool deserializeState(
            const std::vector<std::string>& elements, 
            std::map<SharedState::Key, SharedState::KeyState>& out)
		{
		1+1;

		return deserializeType<BinaryStreamDeserializer>(elements, out);
		}

    bool deserializeLog(
            const std::vector<std::string>& elements, 
            vector<SharedState::LogEntry>& out)
		{
		return deserializeVector<BinaryStreamDeserializer>(elements, out);
		}

    template<class T>
    void serializeForPath(const std::string& path, const T& in, std::string& outSerialized)
        {
        outSerialized = getSerializerForPath(path)->serialize(in);
        }

private:

	serializer_ptr_type getSerializerForPath(const std::string& path)
		{
		auto it = mSerializers.find(path);
		if(it != mSerializers.end())
			return it->second;

		serializer_ptr_type tr = serializer_ptr_type(
					new SerializedObjectStream<BinaryStreamSerializer>()
			);
		mSerializers[path] = tr;
		return tr;
		}



	map<std::string, serializer_ptr_type> mSerializers;
};


}


struct StorageWrapper {
	static boost::shared_ptr<OpenSerializers> jsonSerializersFactory()
		{
		return boost::shared_ptr<OpenSerializers>(new OpenJsonSerializers());
		}

	static boost::shared_ptr<OpenSerializers> binarySerializersFactory()
		{
		return boost::shared_ptr<OpenSerializers>(new OpenBinarySerializers());
		}

	static PolymorphicSharedPtr<FileStorage> createFileStorage(
				string cacheRoot, 
				uint32_t maxOpenFiles,
				float maxLogFileSizeMb
				)
		{
		return PolymorphicSharedPtr<FileStorage>(
			new FileStorage(
				maxLogFileSizeMb, 
				maxOpenFiles, 
				cacheRoot,
				jsonSerializersFactory
				)
			);
		}

	static PolymorphicSharedPtr<FileStorage> createFileStorageMemoOptional(
				string cacheRoot, 
				uint32_t maxOpenFiles,
				float maxLogFileSizeMb,
				bool useMemoChannel
				)
		{
		return PolymorphicSharedPtr<FileStorage>(
			new FileStorage(
				maxLogFileSizeMb, 
				maxOpenFiles, 
				cacheRoot,
				(useMemoChannel ? &jsonSerializersFactory  : &binarySerializersFactory)
				)
			);
		}

	static PolymorphicSharedPtr<KeyspaceStorage> storageForKeyspace(
				PolymorphicSharedPtr<FileStorage>& inStorage,
				Keyspace& inKeyspace,
				int inDimension
				)
		{
		return inStorage->storageForKeyspace(inKeyspace, inDimension);
		}

	static void shutdown_fileStorage(PolymorphicSharedPtr<FileStorage> fileStorage)
		{
		fileStorage->shutdown();
		}


	static void exportPythonInterface()
		{
		using namespace boost::python;
		class_<PolymorphicSharedPtr<FileStorage> >("Storage", no_init)
			.def("storageForKeyspace", storageForKeyspace)
			.def("FileStorage", createFileStorage)
			.def("FileStorage", createFileStorageMemoOptional)
			.def("shutdown", shutdown_fileStorage)
			.staticmethod("FileStorage")
			;

		}

};


struct KeyspaceStorageWrapper {

	static void compress(PolymorphicSharedPtr<KeyspaceStorage>& inStorage)
		{
		inStorage->compress();
		}
	
	static boost::python::object readState( 
											PolymorphicSharedPtr<KeyspaceStorage>& inStorage
											)
		{
		boost::python::dict keystates;

		pair<map<SharedState::Key, KeyState>, vector<LogEntry> > state;

		inStorage->readState(state);

		for (auto it = state.first.begin(); it != state.first.end(); ++it)
			keystates[it->first] = it->second;

		return boost::python::make_tuple(
			keystates,
			Ufora::python::containerWithBeginEndToList(state.second)
			);
		}
	

	static void writeKeyValueMap( 
							PolymorphicSharedPtr<KeyspaceStorage>& inStorage,
							boost::python::dict& keysAndValues
							)
		{
		map<SharedState::Key, KeyState> state;

		boost::python::list keys = keysAndValues.keys();

		long len = boost::python::len(keys);

		for (long k = 0; k < len; k++)
			{
			state[boost::python::extract<SharedState::Key>(keys[k])()] = 
				KeyState(
					null() << ValueType(
						null() << PythonWrapper<SharedState::View>::pyToJsonOrError(keysAndValues[keys[k]]),
						UniqueId()
						),
					null() << UniqueId(),
					std::map<UniqueId, PartialEvent>()
					);
			}

		inStorage->writeStateExternal(state);
		}

	static boost::python::object readKeyValueMap(PolymorphicSharedPtr<KeyspaceStorage>& inStorage)
		{
		boost::python::dict keysAndValues;

		pair<map<SharedState::Key, KeyState>, vector<LogEntry> > state;

		inStorage->readState(state);
		
		inStorage->compressKeyStates(state.first, state.second);

		const KeyType& keyType = KeyTypeFactory::getTypeFor(inStorage->getKeyspace().type());

		for (auto it = state.first.begin(); it != state.first.end(); ++it)
			{
			Nullable<ValueType> val = keyType.computeValueForKeyState(it->second);

			if (val && val->value())
				keysAndValues[it->first] = *val->value();
			}

		return keysAndValues;
		}

	static void writeLogEntry(
											PolymorphicSharedPtr<KeyspaceStorage>& inStorage,
											LogEntry& inLogEntry
											)
		{
		inStorage->writeLogEntry(inLogEntry);
		}

	static void writeLogEntryEvent(
											PolymorphicSharedPtr<KeyspaceStorage>& inStorage,
											PartialEvent& event
											)
		{
		inStorage->writeLogEntry(LogEntry::Event(event));
		}


	static void exportPythonInterface()
		{
		using namespace boost::python;
		class_<PolymorphicSharedPtr<KeyspaceStorage> >("KeyspaceStorage", no_init)
			.def("writeLogEntry", writeLogEntry)
			.def("writeLogEntry", writeLogEntryEvent)
			.def("readState", readState)
			.def("writeKeyValueMap", writeKeyValueMap)
			.def("readKeyValueMap", readKeyValueMap)
			.def("compress", compress)
			;
		}
};




class SharedStateWrapper :
	public native::module::Exporter<SharedStateWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "SharedState";
		}
	void exportPythonWrapper()
		{
		using namespace boost::python;

		PythonWrapper<SharedState::View>::exportPythonInterface();
		StorageWrapper::exportPythonInterface();
		KeyspaceCacheWrapper::exportPythonInterface();
		KeyspaceStorageWrapper::exportPythonInterface();
		}
};


//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<SharedStateWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<SharedStateWrapper>::registerWrapper();






