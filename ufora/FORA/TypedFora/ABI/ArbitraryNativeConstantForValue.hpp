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

#include "../../Serialization/SerializedObjectFlattener.hpp"
#include "../../Native/NativeCode.hppml"
#include "../../Native/ArbitraryNativeConstant.hpp"
#include "../../Core/CSTValue.hppml"

namespace TypedFora {
namespace Abi {

template<class T>
class ArbitraryNativeConstantForValueType : public ArbitraryNativeConstantType {
public:
	virtual std::string getTypename()
		{
		return "ArbitraryNativeConstantForValue<" + 
			Ufora::debug::StackTrace::demangle(typeid(T).name()) + ">";
		}

	virtual boost::shared_ptr<ArbitraryNativeConstant> deserialize(std::string s);

	virtual std::string serialize(boost::shared_ptr<ArbitraryNativeConstant> constant);

	static ArbitraryNativeConstantTypeRegistrar<ArbitraryNativeConstantForValueType<T> > sRegistrar;
};

template<class T>
ArbitraryNativeConstantTypeRegistrar<ArbitraryNativeConstantForValueType<T> > 
ArbitraryNativeConstantForValueType<T>::sRegistrar;

template<class T>
class ArbitraryNativeConstantForValue : public ArbitraryNativeConstant {
public:

	ArbitraryNativeConstantForValue(const T& in) : mValue(in)
		{
		}

	ArbitraryNativeConstantType* type()
		{
		return ArbitraryNativeConstantForValueType<T>::sRegistrar.typePtr();
		}

	NativeType nativeType()
		{
		return NativeTypeFor<T>::get();
		}
	
	void* pointerToData()
		{
		return &mValue;
		}

	std::string description()
		{
		return Ufora::debug::StackTrace::demangle(typeid(T).name()) + "(" + 
				prettyPrintString(mValue) + ")";
		}

	hash_type hash()
		{
		return hashValue(mValue);
		}

	static NativeExpression expressionFor(const T& in)
		{
		return NativeExpression::Constant(
			NativeConstant::ArbitraryConstant(
				boost::shared_ptr<ArbitraryNativeConstant>(
					new ArbitraryNativeConstantForValue<T>(in)
					)
				)
			);
		}

	const T& getValue() const
		{
		return mValue;
		}
	
private:
	T mValue;
};

template<class T>
boost::shared_ptr<ArbitraryNativeConstant> 
ArbitraryNativeConstantForValueType<T>::deserialize(std::string s)
	{
	SerializedObjectInflater inflater;

	T t;

	inflater.inflate(
		PolymorphicSharedPtr<NoncontiguousByteBlock>(
			new NoncontiguousByteBlock(s)
			),
		t
		);

	return boost::shared_ptr<ArbitraryNativeConstant>(
		new ArbitraryNativeConstantForValue<T>(t)
		);
	}

template<class T>
std::string 
ArbitraryNativeConstantForValueType<T>::serialize(boost::shared_ptr<ArbitraryNativeConstant> constant)
	{
	boost::shared_ptr<ArbitraryNativeConstantForValue<T> > c = 
		boost::dynamic_pointer_cast<ArbitraryNativeConstantForValue<T> >(constant);

	lassert(c);

	SerializedObjectFlattener flattener;

	return flattener.flatten(c->getValue())->toString();
	}

}
}
