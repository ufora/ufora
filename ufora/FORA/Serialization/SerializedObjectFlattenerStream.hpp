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

#include "../../core/serialization/SerializedObjectStream.hppml"
#include "SerializedObjectFlattener.hpp"

template<>
class SerializedObjectStream<SerializedObjectFlattenerSerializer> {
public:
	SerializedObjectStream() : 
			mFlattener(),
			mProtocol(mData),
			mStream(mProtocol),
			mSerializer(mFlattener, mStream)
		{
		}

	template<class T>
	std::string serialize(const T& in)
		{
		mSerializer.serialize(in);

		mStream.flush();

		std::string tr(mData.begin(), mData.end());

		mData.resize(0);

		return tr;
		}

	SerializedObjectFlattenerSerializer& getSerializer()
		{
		return mSerializer;
		}

public:
	std::vector<char> mData;

	OMemProtocol mProtocol;

	OBinaryStream mStream;

	SerializedObjectFlattener mFlattener;

	SerializedObjectFlattenerSerializer mSerializer;
};

template<>
class DeserializedObjectStream<SerializedObjectInflaterDeserializer> {
public:
	DeserializedObjectStream() : 
			mInflater(),
			mProtocol((char*)0,0),
			mStream(mProtocol),
			mDeserializer(mInflater, mStream, PolymorphicSharedPtr<VectorDataMemoryManager>())
		{
		}

	template<class T>
	T deserialize(const std::string& in)
		{
		mProtocol.reset(in);

		T out;

		mDeserializer.deserialize(out);
		
		return out;
		}
	
	SerializedObjectInflaterDeserializer& getDeserializer()
		{
		return mDeserializer;
		}

public:
	IMemProtocol mProtocol;

	IBinaryStream mStream;

	SerializedObjectInflater mInflater;

	SerializedObjectInflaterDeserializer mDeserializer;
};

