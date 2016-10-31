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
#include "ArbitraryNativeConstantForString.hpp"

namespace TypedFora {
namespace Abi {

class ArbitraryNativeConstantForStringType : public ArbitraryNativeConstantType {
public:
	virtual std::string getTypename()
		{
		return "String";
		}

	virtual boost::shared_ptr<ArbitraryNativeConstant> deserialize(std::string s)
		{
		return boost::shared_ptr<ArbitraryNativeConstant>(
			new ArbitraryNativeConstantForString(s)
			);
		}

	virtual std::string serialize(boost::shared_ptr<ArbitraryNativeConstant> constant)
		{
		boost::shared_ptr<ArbitraryNativeConstantForString> c =
			boost::dynamic_pointer_cast<ArbitraryNativeConstantForString>(constant);

		lassert(c);

		return c->getString();
		}

	static ArbitraryNativeConstantTypeRegistrar<ArbitraryNativeConstantForStringType> sRegistrar;
};

ArbitraryNativeConstantTypeRegistrar<ArbitraryNativeConstantForStringType>
	ArbitraryNativeConstantForStringType::sRegistrar;




ArbitraryNativeConstantForString::ArbitraryNativeConstantForString(const std::string& value) :
											mValue(value)
	{
	mValuePtr = mValue.c_str();
	}

ArbitraryNativeConstantType* ArbitraryNativeConstantForString::type()
	{
	return ArbitraryNativeConstantForStringType::sRegistrar.typePtr();
	}

NativeType ArbitraryNativeConstantForString::nativeType()
	{
	return NativeType::uint8().ptr();
	}

void* ArbitraryNativeConstantForString::pointerToData()
	{
	return (void*)&mValuePtr;
	}

std::string ArbitraryNativeConstantForString::description()
	{
	return "String(" + mValue + ")";
	}

hash_type ArbitraryNativeConstantForString::hash()
	{
	return hashValue(mValue);
	}

NativeExpression ArbitraryNativeConstantForString::expressionForString(const std::string& in)
	{
	return NativeExpression::Constant(
		NativeConstant::ArbitraryConstant(
			boost::shared_ptr<ArbitraryNativeConstant>(
				new ArbitraryNativeConstantForString(in)
				)
			)
		);
	}

}
}

