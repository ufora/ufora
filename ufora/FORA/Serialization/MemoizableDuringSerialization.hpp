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

#include "../../core/serialization/Serialization.hpp"
#include <boost/bind.hpp>
#include "../../core/math/Hash.hpp"
#include <map>
#include <typeinfo>
#include <boost/thread.hpp>
#include "ForaValueSerializationStream.hppml"

namespace Fora {

namespace MemoizableDuringSerialization {

class MemoStorageBase {
public:
	virtual ~MemoStorageBase() {}

	virtual hash_type hash() const = 0;

	virtual uint32_t size() const = 0;

	virtual void serialize(Fora::ForaValueSerializationStream& serializer) const = 0;

	virtual void deserialize(Fora::ForaValueDeserializationStream& deserializer) = 0;

	virtual bool hasMemo(const void* in) const = 0;

	virtual uint32_t addMemoAndReturnIndex(const void* inValue) = 0;

	virtual uint32_t getMemoIndex(const void* in) const = 0;

	virtual bool hasMemo(uint32_t inIndex) const = 0;

	virtual const void* getMemo(uint32_t inIndex) const = 0;

	virtual void addMemo(uint32_t inIndex, const void* in) = 0;

	//convenience methods
	template<class T>
	bool hasMemo(const T& in) const
		{
		return hasMemo((const void*)&in);
		}

	template<class T>
	uint32_t getMemoIndex(const T& in) const
		{
		return getMemoIndex((const void*)&in);
		}

	template<class T>
	const T& getMemoTyped(uint32_t inIndex) const
		{
		return *(const T*)getMemo(inIndex);
		}

	template<class T>
	uint32_t addMemoAndReturnIndex(const T& inValue)
		{
		return addMemoAndReturnIndex((const void*)&inValue);
		}

	template<class T>
	void addMemo(uint32_t inIndex, const T& in)
		{
		addMemo(inIndex, (const void*)&in);
		}

};

class MemoStorageBaseRegistry {
public:
	MemoStorageBaseRegistry();

	static MemoStorageBaseRegistry& singleton();

	void registerFactory(const char* inType, boost::function0<MemoStorageBase*> inFactory);

	MemoStorageBase* create(const char* inType);

	uint32_t typenameToIndex(const char* inType);

	const char* indexToTypename(uint32_t inType);

private:
	void freeze_();

	boost::mutex mMutex;

	bool mIsFrozen;

	std::map<const char*, uint32_t> mTypeNameIndices;

	std::map<const char*, const char*> mNamesToTypeinfos;

	std::vector<const char*> mTypeinfos;

	std::map<const char*, boost::function0<MemoStorageBase*> > mFactories;
};

template<class T>
class IsMemoizable {
public:
	const static bool isMemoizable = false;

	static bool wantsMemo(const T& in)
		{
		return false;
		}
};


template<bool isMemoizable>
class MemoizeFun;

template<>
class MemoizeFun<true> {
public:
	template<class stream_type, class T>
	static void serialize(
			stream_type& inStream,
			const T& in,
			map<const char*, boost::shared_ptr<MemoStorageBase> >& ioMemos,
			bool alsoSerializeValue
			)
		{
		bool wantsMemo = IsMemoizable<T>::wantsMemo(in);
		inStream.serialize(wantsMemo);

		if (wantsMemo)
			{
			MemoStorageBase* memoPtr;

			if (!ioMemos[typeid(T).name()])
				{
				memoPtr = dynamic_cast<MemoStorageBase*>(
					MemoStorageBaseRegistry::singleton().create(typeid(T).name())
					);
				lassert(memoPtr);

				ioMemos[typeid(T).name()].reset(memoPtr);
				}
			else
				memoPtr = dynamic_cast<MemoStorageBase*>(ioMemos[typeid(T).name()].get());

			if (memoPtr->hasMemo(in))
				inStream.serialize(memoPtr->getMemoIndex(in));
			else
				{
				inStream.serialize(memoPtr->addMemoAndReturnIndex(in));

				if (alsoSerializeValue)
					Serializer<T, stream_type>::serialize(inStream, in);
				}
			}
		else
			Serializer<T, stream_type>::serialize(inStream, in);
		}

	template<class stream_type, class T>
	static void deserialize(
				stream_type& inStream,
				T& out,
				map<const char*, boost::shared_ptr<MemoStorageBase> >& ioMemos,
				bool populateMemo
				)
		{
		bool wantsMemo;
		inStream.deserialize(wantsMemo);

		if (wantsMemo)
			{
			MemoStorageBase* memoPtr;

			if (populateMemo && !ioMemos[typeid(T).name()])
				ioMemos[typeid(T).name()].reset(
					MemoStorageBaseRegistry::singleton().create(typeid(T).name())
					);

			lassert(ioMemos[typeid(T).name()]);

			memoPtr = dynamic_cast<MemoStorageBase*>(ioMemos[typeid(T).name()].get());

			uint32_t index;
			inStream.deserialize(index);

			if (populateMemo && !memoPtr->hasMemo(index))
				{
				Deserializer<T, stream_type>::deserialize(inStream, out);
				memoPtr->addMemo(index, out);
				}
			else
				{
				lassert_dump(
					memoPtr->hasMemo(index),
					"Memo ptr doesn't have " << index << ". total size is " << memoPtr->size()
						<< " and populateMemo = " << (populateMemo?"true":"false")
					);
				out = memoPtr->template getMemoTyped<T>(index);
				}
			}
		else
			Deserializer<T, stream_type>::deserialize(inStream, out);
		}

};

template<>
class MemoizeFun<false> {
public:
	template<class stream_type, class T>
	static void serialize(
				stream_type& inStream,
				const T& in,
				map<const char*, boost::shared_ptr<MemoStorageBase> >& ioMemos,
				bool alsoSerializeValue
				)
		{
		Serializer<T, stream_type>::serialize(inStream, in);
		}

	template<class stream_type, class T>
	static void deserialize(
				stream_type& inStream,
				T& out,
				map<const char*, boost::shared_ptr<MemoStorageBase> >& ioMemos,
				bool populateMemo
				)
		{
		Deserializer<T, stream_type>::deserialize(inStream, out);
		}


};


//MemoStorage has pointer semantics, so be careful copying it around
class MemoStorage {
public:
	MemoStorage()
		{
		}

	MemoStorage(const MemoStorage& in) :
			mMemos(in.mMemos)
		{
		}

	MemoStorage& operator=(const MemoStorage& in)
		{
		mMemos = in.mMemos;

		return *this;
		}

	template<class stream_type, class T>
	void serialize(
				stream_type& inStream,
				const T& in,
				bool alsoSerializeValue
				)
		{
		if (!mMemos)
			mMemos.reset(new map<const char*, boost::shared_ptr<MemoStorageBase> >());

		return MemoizeFun<IsMemoizable<T>::isMemoizable>::serialize(
			inStream,
			in,
			*mMemos,
			alsoSerializeValue
			);
		}

	template<class stream_type, class T>
	void deserialize(
				stream_type& inStream,
				T& out,
				bool populateMemo
				)
		{
		if (!mMemos)
			mMemos.reset(new map<const char*, boost::shared_ptr<MemoStorageBase> >());

		return MemoizeFun<IsMemoizable<T>::isMemoizable>::deserialize(
			inStream,
			out,
			*mMemos,
			populateMemo
			);
		}

	virtual uint32_t size() const
		{
		uint32_t tr = 0;

		if (mMemos)
			for (auto it = mMemos->begin(); it != mMemos->end(); ++it)
				tr = tr + it->second->size();

		return tr;
		}

	hash_type hash() const
		{
		hash_type tr;

		if (mMemos)
			for (auto it = mMemos->begin(); it != mMemos->end(); ++it)
				tr = tr + it->second->hash();

		return tr;
		}

	template<class serializer_type>
	void serializeSelf(serializer_type& s) const
		{
		if (!mMemos)
			{
			s.serialize((uint32_t)0);
			return;
			}

		s.serialize((uint32_t)mMemos->size());

		for (auto it = mMemos->begin(); it != mMemos->end(); ++it)
			{
			s.serialize(MemoStorageBaseRegistry::singleton().typenameToIndex(it->first));
			it->second->serialize(s);
			}
		}

	template<class serializer_type>
	void deserializeSelf(serializer_type& s)
		{
		mMemos.reset(new map<const char*, boost::shared_ptr<MemoStorageBase> >());

		uint32_t count;
		s.deserialize(count);

		for (long k = 0; k < count; k++)
			{
			uint32_t index;
			s.deserialize(index);

			boost::shared_ptr<MemoStorageBase> memo;

			memo.reset(
				MemoStorageBaseRegistry::singleton().create(
					MemoStorageBaseRegistry::singleton().indexToTypename(index)
					)
				);

			memo->deserialize(s);

			(*mMemos)[MemoStorageBaseRegistry::singleton().indexToTypename(index)] = memo;
			}
		}

private:
	boost::shared_ptr<map<const char*, boost::shared_ptr<MemoStorageBase> > > mMemos;
};

}
}


template<class serializer_type>
class Serializer<boost::shared_ptr<Fora::MemoizableDuringSerialization::MemoStorage>, serializer_type> {
public:
		static void serialize(	serializer_type& s,
								const boost::shared_ptr<Fora::MemoizableDuringSerialization::MemoStorage>& t)
			{
			if (!t)
				s.serialize(false);
			else
				{
				s.serialize(true);
				s.serialize(*t);
				}
			}
};

template<class serializer_type>
class Deserializer<boost::shared_ptr<Fora::MemoizableDuringSerialization::MemoStorage>, serializer_type> {
public:
		static void deserialize(serializer_type& s,
								boost::shared_ptr<Fora::MemoizableDuringSerialization::MemoStorage>& t)
			{
			bool hasOne;
			s.deserialize(hasOne);

			if (hasOne)
				{
				t.reset(new Fora::MemoizableDuringSerialization::MemoStorage());
				s.deserialize(*t);
				}
			}
};

template<class serializer_type>
class Serializer<Fora::MemoizableDuringSerialization::MemoStorage, serializer_type> {
public:
		static void serialize(serializer_type& s, const Fora::MemoizableDuringSerialization::MemoStorage& t)
			{
			t.serializeSelf(s);
			}
};

template<class serializer_type>
class Deserializer<Fora::MemoizableDuringSerialization::MemoStorage, serializer_type> {
public:
		static void deserialize(serializer_type& s, Fora::MemoizableDuringSerialization::MemoStorage& t)
			{
			t.deserializeSelf(s);
			}
};



