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

#include "../../../core/serialization/SerializedObjectStream.hppml"
#include "../../../core/serialization/JsonMemoSerializer.hppml"
#include "LogEntry.hppml"


// The scope of a MemoizedSerializer is confined to an individual logfile.



namespace SharedState {

template<class deserializer_type, class T>
bool deserializeType(const std::vector<std::string>& elements, T& out)
    {
    if (elements.size() != 1)
        {
        LOG_WARN << "vector had " << elements.size()
            << " elements != 1";
        return false;
        }
    DeserializedObjectStream<deserializer_type> stream;
    try {
        out = stream.template deserialize<T>(elements[0]);
        }
    catch(...)
        {
        LOG_WARN << "DataError in string vector";
        return false;
        }
    return true;
    }

template<class deserializer_type, class T>
bool deserializeVector(std::vector<std::string> elements, vector<T>& out)
    {
    DeserializedObjectStream<deserializer_type> stream;
    for (long k = 0; k < elements.size();k++)
        try {
            out.push_back(stream.template deserialize<T>(elements[k]));
            }
        catch(std::exception e)
            {
            LOG_WARN << "error during deserialization";
            return false;
            }
        catch(...)
            {
            LOG_WARN << "error during deserialization";
            return false;
            }

    LOG_INFO << "Read " << elements.size() << " elements from sharedState file ";
    return true;
    }


class OpenSerializers : public boost::enable_shared_from_this<OpenSerializers> {
public:
    virtual void serializeLogEntryForPath(
            const std::string& path, 
            const LogEntry& inLog, 
            std::string& outSerialized) = 0;

    virtual std::string serializeStateForPath(
            const std::string& path, 
            const map<SharedState::Key, SharedState::KeyState>& inState) = 0;

    virtual bool deserializeState(
            const std::vector<std::string>& elements, 
            std::map<SharedState::Key, SharedState::KeyState>& out) = 0;

    virtual bool deserializeLog(
            const std::vector<std::string>& elements, 
            vector<SharedState::LogEntry>& out) = 0;

    virtual void finishedWithSerializer(const std::string& path) = 0;


};

class OpenJsonSerializers : public OpenSerializers { 

public:

typedef SerializedObjectStream<JsonMemoSerializer<BinaryStreamSerializer> >
    serializer_type;

typedef boost::shared_ptr<serializer_type>
    serializer_ptr_type;

typedef JsonMemoDeserializer<BinaryStreamDeserializer> 
    deserializer_type;

    void serializeLogEntryForPath(const std::string& path, const LogEntry& inLog, std::string& outSerialized)
        {
        serializeForPath(path, inLog, outSerialized);
        }

    std::string serializeStateForPath(
            const std::string& path, 
            const map<SharedState::Key, SharedState::KeyState>& inState)
        {
        serializer_type serializer;
        return serializer.serialize(inState);
        }

    bool deserializeState(
            const std::vector<std::string>& elements, 
            std::map<SharedState::Key, SharedState::KeyState>& out)
        {
        return deserializeType<deserializer_type>(elements, out);
        }

    bool deserializeLog(
            const std::vector<std::string>& elements, 
            vector<SharedState::LogEntry>& out)
        {
        return deserializeVector<deserializer_type>(elements, out);
        }

    template<class T>
    void serializeForPath(const std::string& path, const T& in, std::string& outSerialized)
        {
        outSerialized = getSerializerForPath(path)->serialize(in);
        }

    void finishedWithSerializer(const std::string& path)
        {
        auto it = mSerializers.find(path);
        if (it != mSerializers.end())
            mSerializers.erase(it);
        }


private:
    serializer_ptr_type getSerializerForPath(const std::string& path);

    map<std::string, serializer_ptr_type> mSerializers;
};

}

