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

#include "../Platform.hpp"
#include "OMemProtocol.hpp"
#include "IMemProtocol.hpp"
#include "OBinaryStream.hpp"
#include "IBinaryStream.hpp"
#include <iostream>
#include <vector>
#include <map>
#include <set>
#include <string>
#include <iostream>
#include <deque>
#include "CPPMLSerializer.hppml"
#include "../Common.hppml"
#include "../python/ScopedPyThreads.hpp"
#include <boost/shared_ptr.hpp>
#include <boost/uuid/uuid.hpp>
#include <boost/uuid/uuid_generators.hpp>
#include <boost/uuid/uuid_io.hpp>
#include <boost/python.hpp>

using namespace std;


template<class T, class storage_type>
class Serializer {
public:
	static void serialize(storage_type& s, const T& t)
		{
		CPPMLSerializer<T, typename T::metadata>::serialize(s,t);
		}
};
template<class T, class storage_type>
class Deserializer {
public:
	static void deserialize(storage_type& s, T& t)
		{
		CPPMLSerializer<T, typename T::metadata>::deserialize(s,t);
		}
};


#define def_binary_serializer(T) 	\
template<class storage_type> class Serializer<T, storage_type> {\
public:\
	static void serialize(storage_type& s, const T& t)\
		{\
		s.writeBytes(&t, sizeof(T));\
		}\
};\
template<class storage_type> class Deserializer<T, storage_type> {\
public:\
	static void deserialize(storage_type& s, T& t)\
		{\
		s.readBytes(&t, sizeof(T));\
		}\
};\



class BinaryStreamSerializer {
public:
	BinaryStreamSerializer(OBinaryStream& s) : mS(s) {}

	void writeBytes(const void* data, uint32_t sz)
		{
		mS.write(sz, (void*)data);
		}
	template<class T>
	void serialize(const T& in)
		{
		Serializer<T, BinaryStreamSerializer>::serialize(*this, in);
		}

	template<class T>
	void serializeSharedPtr(const boost::shared_ptr<T>& in)
		{
		if (!in)
			{
			serialize(false);
			return;
			}
		else
			serialize(true);

		void* ptr = in.get();

		auto it = mSharedPtrToWrittenIndices.find(ptr);

		if (it == mSharedPtrToWrittenIndices.end())
			{
			uint32_t newIndex = mSharedPtrToWrittenIndices.size();
			mSharedPtrToWrittenIndices[ptr] = newIndex;

			serialize(newIndex);
			serialize(*in);
			}
		else
			{
			serialize(it->second);
			}
		}
private:
	OBinaryStream& mS;

	map<void*, uint32_t> mSharedPtrToWrittenIndices;
};


class ByteCountProtocol : public OProtocol {
public:
	ByteCountProtocol() : mCount(0) {}

	void write(uword_t inByteCount, void *inData)
		{
		mCount += inByteCount;
		}

	uword_t position(void)
		{
		return mCount;
		}

private:
	uword_t mCount;
};

class ByteCountSerializer {
public:
	ByteCountSerializer() : mCount(0) {}

	void writeBytes(const void* data, uword_t sz)
		{
		mCount += sz;
		}
	template<class T>
	void serialize(const T& in)
		{
		Serializer<T, ByteCountSerializer>::serialize(*this, in);
		}
	uword_t getCount(void) const
		{
		return mCount;
		}
private:
	uword_t mCount;
};

class BinaryStreamDeserializer {
public:
	BinaryStreamDeserializer(IBinaryStream& s) : mS(s) {}

	void readBytes(void* data, uword_t sz)
		{
		mS.read(sz, data);
		}
	template<class T>
	void deserialize(T& in)
		{
		Deserializer<T, BinaryStreamDeserializer>::deserialize(*this, in);
		}

	template<class T>
	void deserializeSharedPtr(boost::shared_ptr<T>& outPtr)
		{
		bool isNonemptyPointer;

		deserialize(isNonemptyPointer);

		if (!isNonemptyPointer)
			{
			outPtr.reset();
			return;
			}

		uint32_t index;
		deserialize(index);

		if (index >= mIndicesToSharedPtrs.size())
			{
			lassert_dump(index == mIndicesToSharedPtrs.size(),
				"index: " << index << " .vs . " << mIndicesToSharedPtrs.size()
				);

			outPtr.reset(new T());

			mIndicesToSharedPtrs[index] = outPtr;

			deserialize(*outPtr);
			}
		else
			outPtr = boost::static_pointer_cast<T>(mIndicesToSharedPtrs[index]);
		}
private:
	IBinaryStream& mS;

	std::map<uint32_t, boost::shared_ptr<void> > mIndicesToSharedPtrs;
};

template <class T, class serializer_type>
std::string serializeTemplate(const T& in)
	{
	std::vector<char> dat;

		{
		OMemProtocol protocol(dat);
		OBinaryStream stream(protocol);

		serializer_type s(stream);
		Serializer<T, serializer_type>::serialize(s, in);
		}

	return std::string(dat.begin(), dat.end());
	}

template <class T>
std::string serialize(const T& in)
	{
	return serializeTemplate<T, BinaryStreamSerializer>(in);
	}
template <class T>
uword_t serializeCount(const T& in)
	{
	ByteCountSerializer ser;
	Serializer<T, ByteCountSerializer>::serialize(ser, in);
	return ser.getCount();
	}


template <class T, class deserializer_type>
T deserializeTemplate(std::string in)
	{
	IMemProtocol protocol(in);
	IBinaryStream stream(protocol);

	T tr;
	deserializer_type s(stream);
	Deserializer<T, deserializer_type>::deserialize(s, tr);

	return tr;
	}
template <class T>
T deserialize(std::string in)
	{
	return deserializeTemplate<T, BinaryStreamDeserializer>(in);
	}

template <class T>
T deepcopy(const T& in)
	{
	return deserialize<T>(serialize<T>(in));
	}


template<class T, class deserializer_type>
void setStateDeserializeTemplate(T& v, std::string s)
	{
	v = deserializeTemplate<T, deserializer_type>(s);
	}
template<class T>
void setStateDeserialize(T& v, std::string s)
	{
	setStateDeserializeTemplate<T, BinaryStreamDeserializer>(v,s);
	}



def_binary_serializer(bool)
def_binary_serializer(char)
def_binary_serializer(uint8_t)
def_binary_serializer(int8_t)
def_binary_serializer(uint16_t)
def_binary_serializer(int16_t)
def_binary_serializer(uint32_t)
def_binary_serializer(int32_t)
def_binary_serializer(uint64_t)
def_binary_serializer(int64_t)
def_binary_serializer(float)
def_binary_serializer(double)
def_binary_serializer(long double)

#ifdef BSA_PLATFORM_APPLE
def_binary_serializer(long unsigned int)
def_binary_serializer(long)
#endif


template<class T>
OBinaryStream& operator<<(OBinaryStream& s, const T& t)
	{
	BinaryStreamSerializer ser(s);
	Serializer<T, BinaryStreamSerializer>::serialize(ser,t);
	return s;
	}
template<class T>
IBinaryStream& operator>>(IBinaryStream& s, T& t)
	{
	BinaryStreamDeserializer ser(s);
	Deserializer<T, BinaryStreamDeserializer>::deserialize(ser,t);
	return s;
	}

template<class T>
BinaryStreamSerializer& operator<<(BinaryStreamSerializer& s, const T& t)
	{
	Serializer<T, BinaryStreamSerializer>::serialize(s,t);
	return s;
	}
template<class T>
BinaryStreamDeserializer& operator>>(BinaryStreamDeserializer& s, T& t)
	{
	Deserializer<T, BinaryStreamDeserializer>::deserialize(s,t);
	return s;
	}


template<class T1, class T2, class storage_type>
class Serializer<pair<T1, T2>, storage_type> {
public:
	static void serialize(storage_type& s, const pair<T1, T2>& t)
		{
		s.serialize(t.first);
		s.serialize(t.second);
		}
};
template<class T1, class T2, class storage_type>
class Deserializer<pair<T1, T2>, storage_type> {
public:
	static void deserialize(storage_type& s, pair<T1, T2>& t)
		{
		s.deserialize(t.first);
		s.deserialize(t.second);
		}
};


template<class T, class storage_type>
class Serializer<vector<T>, storage_type> {
public:
	static void serialize(storage_type& s, const vector<T>& o)
		{
		uint32_t sz = o.size();
		s.serialize(sz);

		for (int32_t k = 0; k < sz; k++)
			s.serialize(o[k]);
		}
};
template<class T, class storage_type>
class Deserializer<vector<T>, storage_type> {
public:
	static void deserialize(storage_type& s, vector<T>& t)
		{
		uint32_t sz;
		s.deserialize(sz);

		std::deque<T> d;

		for (int32_t k = 0; k < sz; k++)
			{
			T top;
			s.deserialize(top);
			d.push_back(top);
			}

		t = std::vector<T>(d.begin(), d.end());
		}
};

template<class T, class storage_type>
class Serializer<boost::shared_ptr<T>, storage_type> {
public:
	static void serialize(storage_type& s, const boost::shared_ptr<T>& o)
		{
		s.serializeSharedPtr(o);
		}
};

template<class T, class storage_type>
class Deserializer<boost::shared_ptr<T>, storage_type> {
public:
	static void deserialize(storage_type& s, boost::shared_ptr<T>& t)
		{
		s.deserializeSharedPtr(t);
		}
};

template<class T1, class T2, class storage_type>
class Serializer<map<T1, T2>, storage_type> {
public:
	static void serialize(storage_type& s, const map<T1, T2>& o)
		{
		uint32_t sz = o.size();
		s.serialize(sz);

		for (typename std::map<T1,T2>::const_iterator it = o.begin(), it_end = o.end(); it != it_end; ++it)
			{
			s.serialize(it->first);
			s.serialize(it->second);
			}
		}
};

template<class T1, class T2, class storage_type>
class Deserializer<map<T1, T2>, storage_type> {
public:
	static void deserialize(storage_type& s, map<T1, T2>& o)
		{
		o = std::map<T1,T2>();
		uint32_t sz;
		s.deserialize(sz);

		for (int32_t k = 0; k < sz; k++)
			{
			T1 key;
			s.deserialize(key);
			s.deserialize(o[key]);
			}
		}
};

template<class T, class storage_type>
class Serializer<set<T>, storage_type> {
public:
	static void serialize(storage_type& s, const set<T>& o)
		{
		uint32_t sz = o.size();
		s.serialize(sz);

		for (typename std::set<T>::const_iterator it = o.begin(), it_end = o.end(); it != it_end; ++it)
			s.serialize(*it);
		}
};

template<class T, class storage_type>
class Deserializer<set<T>, storage_type> {
public:
	static void deserialize(storage_type& s, set<T>& o)
		{
		o = std::set<T>();
		uint32_t sz;
		s.deserialize(sz);

		for (int32_t k = 0; k < sz; k++)
			{
			T key;
			s.deserialize(key);
			o.insert(key);
			}
		}
};


template<class storage_type>
class Serializer<string, storage_type> {
public:
	static void serialize(storage_type& s, const string& o)
		{
		uint32_t bytes = o.size();
		s.serialize(bytes);

		if (bytes)
			s.writeBytes((void*)&o[0], bytes);
		}
};

template<class storage_type>
class Deserializer<string, storage_type> {
public:
	static void deserialize(storage_type& s, string& o)
		{
		uint32_t bytes;
		s.deserialize(bytes);
		o.resize(bytes);
		if (bytes)
			s.readBytes((void*)&o[0], bytes);
		}
};

template<class storage_type>
class Serializer<boost::uuids::uuid, storage_type> {
public:
	static void serialize(storage_type& s, const boost::uuids::uuid& o)
		{
		Serializer<string, storage_type>::serialize(s, to_string(o));
		}
};

template<class storage_type>
class Deserializer<boost::uuids::uuid, storage_type> {
public:
	static void deserialize(storage_type& s, boost::uuids::uuid& o)
		{
		string temp;
		Deserializer<string, storage_type>::deserialize(s, temp);
		o = boost::uuids::string_generator()(temp);
		}
};


template<class storage_type>
class Serializer<boost::python::object, storage_type> {
public:
	static inline void serialize(	storage_type& s,
									const boost::python::object& o
									)
		{
		ScopedPyThreadsReacquire reaquire;

		boost::python::object cPickleModule =
						boost::python::import("cPickle");
		boost::python::object res =
			cPickleModule.attr("dumps")(o, 2);

		boost::python::extract<string> extracter(res);
		if (extracter.check())
			s.serialize(extracter());
			else
			{
			throw std::logic_error("unable to pickle a python object");
			}
		}
};

template<class storage_type>
class Deserializer<boost::python::object, storage_type> {
public:
	static inline void deserialize(	storage_type& s,
									boost::python::object& o
									)
		{
		std::string pickledData;
		s.deserialize(pickledData);

		ScopedPyThreadsReacquire reaquire;

		boost::python::object cPickleModule =
						boost::python::import("cPickle");
		o = cPickleModule.attr("loads")(pickledData);
		}
};


