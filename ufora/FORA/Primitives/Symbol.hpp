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
#ifndef Symbol_hpp
#define Symbol_hpp

#include <string>
#include <stdint.h>
#include "../../core/math/Hash.hpp"
#include "../../core/cppml/CPPMLEquality.hppml"
#include "../../core/cppml/CPPMLPrettyPrinter.hppml"
#include "../../core/serialization/Serialization.hpp"

class Symbol {
		class SymbolData {
		public:
			std::string string;
			hash_type hash;
		};
public:
		Symbol(const Symbol& in)
			{
			mSymbolDataPtr = in.mSymbolDataPtr;
			}
		Symbol(const std::string& in)
			{
			mSymbolDataPtr = intern(in.c_str());
			}
		Symbol()
			{
			mSymbolDataPtr = 0;
			}
		hash_type hash() const
			{
			return hashFor(mSymbolDataPtr);
			}
		std::string toString() const
			{
			return stringFor(mSymbolDataPtr);
			}
		size_t size() const
			{
			return sizeFor(mSymbolDataPtr);
			}
		char cmp(const Symbol& in) const
			{
			if (!mSymbolDataPtr && !in.mSymbolDataPtr)
				return 0;
			if (mSymbolDataPtr && !in.mSymbolDataPtr)
				return 1;
			if (!mSymbolDataPtr && in.mSymbolDataPtr)
				return -1;

			return hashFor(mSymbolDataPtr).cmp(hashFor(in.mSymbolDataPtr));
			}
		Symbol& operator=(const Symbol& in)
			{
			mSymbolDataPtr = in.mSymbolDataPtr;
			return *this;
			}
		bool operator==(const Symbol& in) const
			{
			return mSymbolDataPtr == in.mSymbolDataPtr;
			}

		#define Symbol__cache_item(x,y)	\
		static Symbol x();

		Symbol__cache_item(Call, "Call")
		Symbol__cache_item(SetCall, "SetCall")
		Symbol__cache_item(Member, "Member")
		Symbol__cache_item(SetMember, "SetMember")
		Symbol__cache_item(GetItem, "GetItem")
		Symbol__cache_item(SetItem, "SetItem")
		Symbol__cache_item(Iter, "Iter")
		Symbol__cache_item(Next, "Next")
		Symbol__cache_item(Operator, "Operator")
		Symbol__cache_item(LeftOperator, "LeftOperator")
		Symbol__cache_item(RightOperator, "RightOperator")
		Symbol__cache_item(ReverseOperator, "ReverseOperator")
		Symbol__cache_item(Convert, "Convert")
		Symbol__cache_item(MakeTuple, "MakeTuple")
		Symbol__cache_item(Alternative, "Alternative")
		Symbol__cache_item(Symbol_, "Symbol")
		Symbol__cache_item(Type, "Type")
		Symbol__cache_item(Function, "Function")
		Symbol__cache_item(Vector, "Vector")
		Symbol__cache_item(Nothing, "Nothing")
		Symbol__cache_item(StackTrace, "StackTrace")
		Symbol__cache_item(String, "String")
		Symbol__cache_item(Integer, "Integer")
		Symbol__cache_item(Float, "Float")
		Symbol__cache_item(Tuple, "Tuple")
		Symbol__cache_item(Structure, "Structure")
		Symbol__cache_item(Class, "Class")
		Symbol__cache_item(Sin, "Sin")
		Symbol__cache_item(Cos, "Cos")
		Symbol__cache_item(Log, "Log")
		Symbol__cache_item(Exp, "Exp")
		Symbol__cache_item(Is, "Is")
		Symbol__cache_item(And, "And")
		Symbol__cache_item(Or, "Or")
		Symbol__cache_item(Dictionary, "Dictionary")
		Symbol__cache_item(DateTime, "DateTime")
		Symbol__cache_item(TimeDuration, "TimeDuration")
		Symbol__cache_item(Extras, "Extras")

private:
		static const hash_type& hashFor(const SymbolData* symbol)
			{
			if (!symbol)
				{
				static hash_type h;

				return h;
				}
			return symbol->hash;
			}

		static const std::string& stringFor(const SymbolData* symbol)
			{
			if (!symbol)
				{
				static std::string emptyString;
				return emptyString;
				}

			return symbol->string;
			}

		static size_t sizeFor(const SymbolData* symbol)
			{
			if (!symbol)
				return 0;

			return symbol->string.size();
			}

		SymbolData*	mSymbolDataPtr;	//the first part is the first few bytes
											//of the hash. the second part is
											//a counter of the number of times
											//we've seen that particular hash-prefix
											//before.
		static SymbolData* intern(const std::string& data);
};

//convert a string to a symbol that's safe for user-code. Makes sure that no
//spaces or other nonstandard characters get into the symbol.
Symbol stringToSymbolSafe(std::string s);

template<>
class CPPMLEquality<Symbol, void> {
public:
		static char cmp(const Symbol& lhs, const Symbol& rhs)
			{
			return lhs.cmp(rhs);
			}
};

template<class storage_type>
class Serializer<Symbol, storage_type> {
public:
		static void serialize(storage_type& s, const Symbol& o)
			{
			s.serialize(o.toString());
			}
};
template<class storage_type>
class Deserializer<Symbol, storage_type> {
public:
		static void deserialize(storage_type& s, Symbol& o)
			{
			std::string st;
			s.deserialize(st);

			o = Symbol(st);
			}
};

template<>
class CPPMLPrettyPrint<Symbol> {
public:
		static void prettyPrint(CPPMLPrettyPrintStream& stream, const Symbol& toPr)
			{
			stream << toPr.toString();
			}
};

template<class T, class T2>
class CPPMLTransform;

template<>
class CPPMLTransform<Symbol, void> {
public:
		template<class F>
		static Nullable<Symbol> apply(const Symbol& in, const F& f)
			{
			return null();
			}
};


template<class T, class T2>
class CPPMLTransformWithIndex;

template<>
class CPPMLTransformWithIndex<Symbol, void> {
public:
		template<class F, class F2>
		static Nullable<Symbol> apply(const Symbol& in, const F& f, const F2& f2)
			{
			return null();
			}
};

template<class T, class T2>
class CPPMLVisit;

template<>
class CPPMLVisit<Symbol, void> {
public:
		template<class F>
		static void apply(const Symbol& in, F& f)
			{
			}
};

template<class T, class T2>
class CPPMLVisitWithIndex;

template<>
class CPPMLVisitWithIndex<Symbol, void> {
public:
		template<class F, class indices_type>
		static void apply(const Symbol& in, const F& f, const indices_type& inIndices)
			{
			}
};

inline bool operator<(const Symbol & lhs, const Symbol & rhs)
	{
	return lhs.cmp(rhs) < 0;
	}
inline bool operator!=(const Symbol & lhs, const Symbol & rhs)
	{
	return !(lhs == rhs);
	}

macro_defineMemberHashFunction(Symbol)

#endif

