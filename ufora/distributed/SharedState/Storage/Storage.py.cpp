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
#include <boost/python.hpp>

#include "LogFileDirectory.hppml"
#include "LogFileSerialization.hpp"
#include "FileKeyspaceStorage.hppml"
#include "ChecksummedFile.hpp"
#include "LogEntry.hppml"
#include "OpenFiles.hpp"

#include "../../../core/python/ScopedPyThreads.hpp"
#include "../../../core/PolymorphicSharedPtr.hpp"
#include "../../../core/python/ScopedPyThreads.hpp"
#include "../../../core/python/CPPMLWrapper.hpp"
#include "../../../core/threading/Queue.hpp"
#include "../../../native/Registrar.hpp"


using namespace ChecksummedFile;

namespace {
    boost::python::list vectorToList(const std::vector<string>& inVector)
        {
        boost::python::list tr;
        for(int i = 0; i < inVector.size(); i++)
            tr.append(inVector[i]);
        return tr;
        }

    std::vector<string> listToStringVec(const boost::python::list inList)
        {
        std::vector<std::string> toWrite;
        int len = boost::python::extract<int>(inList.attr("__len__")());
        for(int i = 0; i < len; i++)
            toWrite.push_back(boost::python::extract<std::string>(inList[i]));
        return toWrite;
        }

}


class ChecksummedFileWrapper {
public:
    static boost::shared_ptr<ChecksummedFile::ChecksummedWriter> newChecksummedWriter(const std::string& path)
        {
        return boost::shared_ptr<ChecksummedWriter>(new ChecksummedWriter(path));
        }

    static std::string path(boost::shared_ptr<ChecksummedFile::ChecksummedWriter>& writer)
        {
        return writer->path();
        }

    static void flush(boost::shared_ptr<ChecksummedFile::ChecksummedWriter>& writer)
        {
        writer->flush();
        }

    static uint64_t written(boost::shared_ptr<ChecksummedFile::ChecksummedWriter>& writer)
        {
        return writer->written();
        }

    static uint64_t fileSize(boost::shared_ptr<ChecksummedFile::ChecksummedWriter>& writer)
        {
        return writer->fileSize();
        }

    static void writeString(
            boost::shared_ptr<ChecksummedFile::ChecksummedWriter>& writer,
            const std::string inString)
        {
        writer->writeString(inString);
        }

    static boost::python::tuple readToList(const std::string& path)
        {
        std::vector<string> out;
        bool tr = ChecksummedFile::readAllToVector(path, out);
        return boost::python::make_tuple(tr, vectorToList(out));
        }

    static void exportPythonWrapper()
        {
        using namespace boost::python;
        class_<boost::shared_ptr<ChecksummedWriter> >("ChecksummedWriter")
            .def("path", &path)
            .def("flush", &flush)
            .def("written", &written)
            .def("fileSize", &fileSize)
            .def("writeString", &writeString)
            ;
        def("ChecksummedWriter", &newChecksummedWriter);
        def("readToVector", &readToList);

        }
};


namespace SharedState {

class LogFileDirectoryWrapper {
public:
    static boost::python::dict getAllLogFiles(LogFileDirectory& directory)
        {
        boost::python::dict tr;
        map<uint32_t, string> files = directory.getAllLogFiles();
        for(auto it = files.begin(); it != files.end(); ++it)
            tr[it->first] = it->second;
        return tr;
        }

    static boost::python::dict getAllStateFiles(LogFileDirectory& directory)
        {
        boost::python::dict tr;
        map<uint32_t, string> files = directory.getAllStateFiles();
        for(auto it = files.begin(); it != files.end(); ++it)
            tr[it->first] = it->second;
        return tr;
        }

    static void exportPythonWrapper()
        {
        using namespace boost::python;

        class_<LogFileDirectory>("LogFileDirectory", init<std::string, Keyspace, KeyRange>())
            .def("getAllLogFiles", &getAllLogFiles)
            .def("getAllStateFiles", &getAllStateFiles)
            .def("startNextLogFile", &LogFileDirectory::startNextLogFile)
            .def("getCurrentLogPath", &LogFileDirectory::getCurrentLogPath)
            .def("getNextStatePath", &LogFileDirectory::getNextStatePath)
            ;
        }
};


class OpenFilesWrapper {
public:
    typedef boost::shared_ptr<OpenFilesInterface> open_files_ptr;

    static open_files_ptr createOpenFiles(uint32_t maxFiles)
        {
        return open_files_ptr(new OpenFiles(maxFiles));
        }

    static void append(open_files_ptr files, const std::string& path, const std::string& contents)
        {
        files->append(path, contents);
        }

    static bool readToVector(
            open_files_ptr files,
            const std::string& path
            )
        {
        std::vector<std::string> outVector;
        bool success = files->readFileAsStringVector(path, outVector);
        return boost::python::make_tuple(success, vectorToList(outVector));
        }

    static uint64_t written(open_files_ptr files, const std::string& path)
        {
        return files->written(path);
        }

    static void flush(open_files_ptr files, const std::string& path)
        {
        files->flush(path);
        }

    static void shutdown(open_files_ptr files)
        {
        files->shutdown();
        }

    static void exportPythonWrapper()
        {
        using namespace boost::python;
        class_<open_files_ptr>("OpenFiles")
            .def("append", &append)
            .def("readToVector", &readToVector)
            .def("written", &written)
            .def("flush", &flush)
            .def("shutdown", &shutdown)
            ;
        def("OpenFiles", &createOpenFiles);
        }
};


class LogFileSerializationWrapper {
public:

    static boost::shared_ptr<OpenJsonSerializers> newOpenJsonSerializers()
        {
        return boost::shared_ptr<OpenJsonSerializers>(new OpenJsonSerializers());
        }

    static boost::python::tuple deserializeAsType(const std::string& serialized)
        {
        std::vector<std::string> inSerialized;
        inSerialized.push_back(serialized);

        std::vector<string> outVec;
        bool success = deserializeType<OpenJsonSerializers::deserializer_type>(inSerialized, outVec);
        return boost::python::make_tuple(success, vectorToList(outVec));
        }

    static boost::python::tuple deserializeAsVector(boost::python::list inList)
        {
        std::vector<std::string> inSerialized = listToStringVec(inList);
        std::vector<string> outVec;
        bool success = deserializeVector<OpenJsonSerializers::deserializer_type>(inSerialized, outVec);
        return boost::python::make_tuple(success, vectorToList(outVec));
        }

    static std::string serializeVector(
            boost::shared_ptr<OpenJsonSerializers>& serializers,
            const std::string& path,
            boost::python::list inList)
        {


        std::vector<std::string> toWrite = listToStringVec(inList);
        std::string out;

        serializers->serializeForPath(path, toWrite, out);
        return out;
        }

    static std::string serialize(
            boost::shared_ptr<OpenJsonSerializers>& serializers,
            const std::string& path,
            const std::string& value)
        {
        std::string out;
        serializers->serializeForPath(path, value, out);
        return out;
        }

    static void exportPythonWrapper()
        {
        using namespace boost::python;
        class_<boost::shared_ptr<OpenJsonSerializers> >("OpenJsonSerializers")
            .def("serialize", &serialize)
            .def("serializeAsVector", &serializeVector)
            ;
        def("OpenJsonSerializers", &newOpenJsonSerializers);
        def("deserializeAsType", &deserializeAsType);
        def("deserializeAsVector", &deserializeAsVector);
        }
};


class PythonOpenFiles : public OpenFilesInterface {
public:
    PythonOpenFiles(
            boost::python::object inAppendFun,
            boost::python::object inWrittenFun,
            boost::python::object inFlushFun,
            boost::python::object inReadFileAsStringVectorFun) :
        mAppendFun(inAppendFun),
        mWrittenFun(inWrittenFun),
        mFlushFun(inFlushFun),
        mReadFileAsStringVectorFun(inReadFileAsStringVectorFun)
        {
        }

    virtual ~PythonOpenFiles() = default;

    void shutdown()
        {
        }

    void closeFile(const std::string& path)
        {
        }

    void append(const std::string& path, const std::string& contents)
        {
	boost::recursive_mutex::scoped_lock lock(mMutex);
        mAppendFun(path, contents);
        }

    uint64_t written(const std::string& path) const
        {
	boost::recursive_mutex::scoped_lock lock(mMutex);
        boost::python::object toPut = boost::python::make_tuple("written", path);
        return boost::python::extract<uint64_t>(mWrittenFun(path));
        }

    void flush(const std::string& path)
        {
	boost::recursive_mutex::scoped_lock lock(mMutex);
        mFlushFun(path);
        }

    bool readFileAsStringVector(const std::string& path, std::vector<std::string>& out) const
        {
        using namespace boost::python;
	boost::recursive_mutex::scoped_lock lock(mMutex);
        boost::python::tuple outTuple = extract<boost::python::tuple>(mReadFileAsStringVectorFun(path));
        out = listToStringVec(extract<boost::python::list>(outTuple[1]));
        return extract<bool>(outTuple[0]);
        }

    //
    // python wrapper stuff

    static boost::shared_ptr<PythonOpenFiles> newPythonOpenFiles(
            boost::python::object inAppendFun,
            boost::python::object inWrittenFun,
            boost::python::object inFlushFun,
            boost::python::object inReadFileAsStringVectorFun)
        {
        return boost::shared_ptr<PythonOpenFiles>(new PythonOpenFiles(
                    inAppendFun,
                    inWrittenFun,
                    inFlushFun,
                    inReadFileAsStringVectorFun)
                );
        }
    static boost::shared_ptr<OpenFilesInterface> asInterface(boost::shared_ptr<PythonOpenFiles> inOpenFiles)
        {
        return boost::shared_ptr<OpenFilesInterface>(inOpenFiles);
        }
    static void exportPythonWrapper()
        {
        using namespace boost::python;
        class_<boost::shared_ptr<PythonOpenFiles> >("PythonOpenFiles")
            .def("asInterface", &asInterface)
            ;
        def("PythonOpenFiles", newPythonOpenFiles);
        }

private:
        boost::python::object mAppendFun;
        boost::python::object mWrittenFun;
        boost::python::object mFlushFun;
        boost::python::object mReadFileAsStringVectorFun;
        mutable boost::recursive_mutex mMutex;
};


class FileKeyspaceStorageWrapper {
public:
    static LogEntry logEntryId(uint64_t inId)
        {
        return LogEntry::Id(inId);
        }

    static void writeLogEntry(boost::shared_ptr<FileKeyspaceStorage> inStorage, const LogEntry& inEntry)
        {
        inStorage->writeLogEntry(inEntry);
        }

    static void compress(boost::shared_ptr<FileKeyspaceStorage> inStorage)
        {
        inStorage->compress();
        }

    static LogEntry logEntryUpdate(Key key, Ufora::Json update, uint64_t updateId)
        {
        return LogEntry::Event(
                createPartialEventNullable(key, Nullable<Ufora::Json>(update), updateId, 0));
        }


    static PartialEvent createPartialEvent(Key key, boost::python::object pyUpdate, uint64_t updateId, uint32_t clientId)
        {
        Nullable<Ufora::Json> update;
        if (pyUpdate != boost::python::object())
            update = Nullable<Ufora::Json>(boost::python::extract<Ufora::Json>(pyUpdate));
        return createPartialEventNullable(key, update, updateId, clientId);


        }

    static PartialEvent createPartialEventNullable(Key key, Nullable<Ufora::Json> update, uint64_t updateId, uint32_t clientId)
        {
        KeyUpdate content(key, update);
        set<Key> keySet;
        keySet.insert(key);
        UniqueId id(updateId, clientId);
        EventSignature signature(keySet, id);
        return PartialEvent(content, signature);
        }

    static boost::shared_ptr<OpenSerializers> newOpenJsonSerializers()
        {
        return boost::shared_ptr<OpenSerializers>(new OpenJsonSerializers());

        }

    static boost::shared_ptr<FileKeyspaceStorage> newFileKeyspaceStorage(
            string cacheDirectory,
            Keyspace inKeyspace,
            KeyRange inKeyRange,
            boost::shared_ptr<OpenFilesInterface> openFiles,
            float maxLogSizeMB)
        {
        return boost::shared_ptr<FileKeyspaceStorage>(
            new FileKeyspaceStorage(
                cacheDirectory,
                inKeyspace,
                inKeyRange,
                openFiles,
                &newOpenJsonSerializers,
                maxLogSizeMB)
            );
        }

    static boost::python::tuple deserializeLogEntry(const std::string& serialized)
        {
        std::vector<std::string> elements;
        elements.push_back(serialized);
        LogEntry tr;
        bool success = deserializeType<OpenJsonSerializers::deserializer_type>(elements, tr);
        return boost::python::make_tuple(success, tr);
        }

    static boost::python::object deserializeAllLogEntries(boost::python::list inList)
        {
        std::vector<std::string> elements = listToStringVec(inList);
        std::vector<LogEntry> out;
        bool success = deserializeVector<OpenJsonSerializers::deserializer_type>(elements, out);
        boost::python::list outList;
        for(int i = 0; i < out.size(); i++)
            outList.append(out[i]);
        return boost::python::make_tuple(success, outList);
        }
    static void exportPythonWrapper() {
        using namespace boost::python;
        class_<boost::shared_ptr<FileKeyspaceStorage> >("FileKeyspaceStorage")
            .def("writeLogEntry", writeLogEntry)
            .def("compress", compress)
            ;
        def("FileKeyspaceStorage", &newFileKeyspaceStorage);
        def("createLogEntryId", &logEntryId);
        def("createLogEntryEvent", &logEntryUpdate);
        def("createPartialEvent", &createPartialEvent);
        def("deserializeLogEntry", &deserializeLogEntry);
        def("deserializeAllLogEntries", &deserializeAllLogEntries);

    }
};


class StorageTestNative {
public:
    // place for putting c++ test functions
    static void writeToOpenFiles(
            boost::shared_ptr<OpenFilesInterface> openFiles,
            boost::python::list inFilenames,
            boost::python::list inStringsToWrite,
            uint64_t numIterations)
        {
        vector<string> filenames = listToStringVec(inFilenames);
        vector<string> contents = listToStringVec(inStringsToWrite);
            {
            ScopedPyThreads scopedGILUnlocker;
            for(int i = 0; i < numIterations; i++)
                for(int j = 0; j < filenames.size(); j++)
                    for(int k = 0; k < contents.size(); k++)
                        openFiles->append(filenames[j], contents[k]);
            }
        }
    static void exportPythonWrapper()
        {
        def("writeToOpenFiles", &writeToOpenFiles);
        }
};

class StorageWrapper :
    public native::module::Exporter<StorageWrapper> {

    std::string getModuleName(void)
        {
        return "Storage";
        }

    void exportPythonWrapper()
        {
        using namespace boost::python;

        LogFileDirectoryWrapper::exportPythonWrapper();
        ChecksummedFileWrapper::exportPythonWrapper();
        OpenFilesWrapper::exportPythonWrapper();
        LogFileSerializationWrapper::exportPythonWrapper();
        PythonOpenFiles::exportPythonWrapper();
        FileKeyspaceStorageWrapper::exportPythonWrapper();
        StorageTestNative::exportPythonWrapper();
        }
};

}


//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<SharedState::StorageWrapper>::mEnforceRegistration =
    native::module::ExportRegistrar<SharedState::StorageWrapper>::registerWrapper();

