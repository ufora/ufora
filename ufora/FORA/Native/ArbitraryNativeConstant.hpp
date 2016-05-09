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

#include <boost/shared_ptr.hpp>
#include "NativeType.hppml"
#include "../../core/cppml/CPPMLEquality.fwd.hppml"
#include "../../core/math/Hash.hpp"

class ArbitraryNativeConstant;
class ArbitraryNativeConstantType;

class ArbitraryNativeConstantTypeRegistry {
public:
	static ArbitraryNativeConstantTypeRegistry& singleton();

	void registerType(ArbitraryNativeConstantType* type);

	ArbitraryNativeConstantType* lookup(std::string typeName);

private:
	static boost::mutex mMutex;

	static map<std::string, ArbitraryNativeConstantType*> mTypeTable;
};


template<class T>
class ArbitraryNativeConstantTypeRegistrar {
public:
	ArbitraryNativeConstantTypeRegistrar() : mTypePtr(new T)
		{
		ArbitraryNativeConstantTypeRegistry::singleton().registerType(mTypePtr);
		}

	T* typePtr()
		{
		return mTypePtr;
		}

private:
	T* mTypePtr;
};

class ArbitraryNativeConstantType {
public:
	virtual std::string getTypename() = 0;

	virtual boost::shared_ptr<ArbitraryNativeConstant> deserialize(std::string s) = 0;

	virtual std::string serialize(boost::shared_ptr<ArbitraryNativeConstant> constant) = 0;
};

class ArbitraryNativeConstant {
public:
	virtual ArbitraryNativeConstantType* type() = 0;

	//return the native type of the constant
	virtual NativeType nativeType() = 0;

	//return a pointer to the data
	virtual void* pointerToData() = 0;

	virtual std::string description() = 0;

	virtual hash_type hash() = 0;
};

template<>
class CPPMLEquality<boost::shared_ptr<ArbitraryNativeConstant>, void> {
public:
	static char cmp(const boost::shared_ptr<ArbitraryNativeConstant>& lhs,
					const boost::shared_ptr<ArbitraryNativeConstant>& rhs
					)
		{
		if (lhs->type()->getTypename() < rhs->type()->getTypename())
			return -1;
		if (lhs->type()->getTypename() > rhs->type()->getTypename())
			return 1;

		return cppmlCmp(lhs->hash(), rhs->hash());
		}
};

template<>
class Serializer<boost::shared_ptr<ArbitraryNativeConstant>, HashingStreamSerializer> {
public:
	static inline void serialize(
						HashingStreamSerializer& s,
						const boost::shared_ptr<ArbitraryNativeConstant>& in
						)
		{
		s.serialize(in->type()->getTypename());
		s.serialize(in->hash());
		}
};

template<class serializer_type>
class Serializer<boost::shared_ptr<ArbitraryNativeConstant>, serializer_type> {
public:
		static void serialize(serializer_type& s, const boost::shared_ptr<ArbitraryNativeConstant>& t)
			{
			s.serialize(t->type()->getTypename());
			s.serialize(t->type()->serialize(t));
			}
};

template<class serializer_type>
class Deserializer<boost::shared_ptr<ArbitraryNativeConstant>, serializer_type> {
public:
		static void deserialize(serializer_type& s, boost::shared_ptr<ArbitraryNativeConstant>& t)
			{
			std::string typeName, data;
			s.deserialize(typeName);
			s.deserialize(data);

			t = ArbitraryNativeConstantTypeRegistry::singleton().lookup(typeName)->deserialize(data);
			}
};


template<>
class CPPMLPrettyPrint<boost::shared_ptr<ArbitraryNativeConstant> > {
public:
		static void prettyPrint(CPPMLPrettyPrintStream& s, const boost::shared_ptr<ArbitraryNativeConstant>& t)
			{
			s << t->description();
			}
};

template<class T, class T2>
class CPPMLTransform;

template<>
class CPPMLTransform<boost::shared_ptr<ArbitraryNativeConstant>, void> {
public:
		template<class F>
		static Nullable<boost::shared_ptr<ArbitraryNativeConstant> > apply(const boost::shared_ptr<ArbitraryNativeConstant>& in, const F& f)
			{
			return null();
			}
};
template<class T, class T2>
class CPPMLTransformWithIndex;

template<>
class CPPMLTransformWithIndex<boost::shared_ptr<ArbitraryNativeConstant>, void> {
public:
		template<class F, class F2>
		static Nullable<boost::shared_ptr<ArbitraryNativeConstant> > apply(const boost::shared_ptr<ArbitraryNativeConstant>& in, const F& f, const F2& f2)
			{
			return null();
			}
};

template<class T, class T2>
class CPPMLVisit;

template<>
class CPPMLVisit<boost::shared_ptr<ArbitraryNativeConstant>, void> {
public:
		template<class F>
		static void apply(const boost::shared_ptr<ArbitraryNativeConstant>& in, const F& f)
			{
			}
};
template<class T, class T2>
class CPPMLVisitWithIndex;

template<>
class CPPMLVisitWithIndex<boost::shared_ptr<ArbitraryNativeConstant>, void> {
public:
		template<class F, class F2>
		static void apply(const boost::shared_ptr<ArbitraryNativeConstant>& in, const F& f, const F2& inF2)
			{
			}
};
