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
#include "Symbol.hpp"
#include "String.hppml"
#include "../Axioms/ReturnValue.hpp"
#include "../Core/Type.hppml"
#include "../Core/ExecutionContext.hppml"
#include "../../core/math/Hash.hpp"
#include <boost/unordered_map.hpp>
#include <boost/thread.hpp>

using namespace std;
using namespace Fora;

namespace {

boost::recursive_mutex				FORA_Symbol__mutex;

}

Symbol::SymbolData*	Symbol::intern(const std::string& data)
	{
	Hash hash = Hash::CityHash(data);
	
	boost::recursive_mutex::scoped_lock lock(FORA_Symbol__mutex);
	
	static boost::unordered_map<hash_type, SymbolData*> symbolMap;

	if (!symbolMap.size())
		symbolMap[Hash::CityHash(string(""))] = 0;

	auto it = symbolMap.find(hash);

	if (it != symbolMap.end())
		return it->second;

	SymbolData* symbolData = new SymbolData();
	symbolData->string = data;
	symbolData->hash = hash;

	symbolMap[hash] = symbolData;

	return symbolData;
	}

#define Symbol__cache_item_body(x, y)	\
Symbol Symbol::x()						\
	{									\
	static Symbol* s = 0;				\
	if (!s)								\
		s = new Symbol(Symbol(y));		\
	return *s;							\
	}									

Symbol__cache_item_body(Call, "Call")
Symbol__cache_item_body(SetCall, "SetCall")
Symbol__cache_item_body(Member, "Member")
Symbol__cache_item_body(SetMember, "SetMember")
Symbol__cache_item_body(GetItem, "GetItem")
Symbol__cache_item_body(SetItem, "SetItem")
Symbol__cache_item_body(Iter, "Iter")
Symbol__cache_item_body(Next, "Next")
Symbol__cache_item_body(Operator, "Operator")
Symbol__cache_item_body(LeftOperator, "LeftOperator")
Symbol__cache_item_body(RightOperator, "RightOperator")
Symbol__cache_item_body(ReverseOperator, "ReverseOperator")
Symbol__cache_item_body(Convert, "Convert")
Symbol__cache_item_body(MakeTuple, "MakeTuple")
Symbol__cache_item_body(Alternative, "Alternative")
Symbol__cache_item_body(Symbol_, "Symbol")
Symbol__cache_item_body(Type, "Type")
Symbol__cache_item_body(Function, "Function")
Symbol__cache_item_body(Vector, "Vector")
Symbol__cache_item_body(Nothing, "Nothing")
Symbol__cache_item_body(StackTrace, "StackTrace")
Symbol__cache_item_body(String, "String")
Symbol__cache_item_body(Integer, "Integer")
Symbol__cache_item_body(Float, "Float")
Symbol__cache_item_body(Tuple, "Tuple")
Symbol__cache_item_body(Structure, "Structure")
Symbol__cache_item_body(Class, "Class")
Symbol__cache_item_body(Sin, "Sin")
Symbol__cache_item_body(Cos, "Cos")
Symbol__cache_item_body(Log, "Log")
Symbol__cache_item_body(Exp, "Exp")
Symbol__cache_item_body(Is, "Is")
Symbol__cache_item_body(And, "And")
Symbol__cache_item_body(Or, "Or")
Symbol__cache_item_body(Dictionary, "Dictionary")
Symbol__cache_item_body(Extras, "Extras")

Symbol stringToSymbolSafe(std::string s)
	{
	for (long k = 0; k < s.size(); k++)
		if (!isalnum(s[k]) && s[k] != '_')
			s[k] = '_';
		
	return Symbol(s);
	}

extern "C" {

BSA_DLLEXPORT
ReturnValue<Symbol> FORA_clib_stringToSymbolSafe(const String& inString)
	{
	return slot0(stringToSymbolSafe(inString.stdString()));
	}

BSA_DLLEXPORT
ReturnValue<String> FORA_clib_symbolToString(const Symbol& in)
	{
	return slot0(
		String(
			in.toString(),
			Fora::Interpreter::ExecutionContext::currentExecutionContext()->getMemoryPool()
			)
		);
	}

};

