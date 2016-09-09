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
#include "ArbitraryNativeConstantForCSTValue.hpp"
#include "../../Serialization/SerializedObjectFlattener.hpp"
#include "ImplValNativeCodeModel.hppml"
#include "NativeLayoutType.hppml"

namespace TypedFora {
namespace Abi {

class ArbitraryNativeConstantForCSTValueType : public ArbitraryNativeConstantType {
public:
	virtual std::string getTypename()
		{
		return "CSTValue";
		}

	virtual boost::shared_ptr<ArbitraryNativeConstant> deserialize(std::string s)
		{
		pair<CSTValue, bool> p;

		SerializedObjectInflater inflater;

		inflater.inflate(
			PolymorphicSharedPtr<NoncontiguousByteBlock>(
				new NoncontiguousByteBlock(std::move(s))
				),
			p
			);

		return boost::shared_ptr<ArbitraryNativeConstant>(
			new ArbitraryNativeConstantForCSTValue(
				p.first,
				p.second
				)
			);
		}

	virtual std::string serialize(boost::shared_ptr<ArbitraryNativeConstant> constant)
		{
		boost::shared_ptr<ArbitraryNativeConstantForCSTValue> c =
			boost::dynamic_pointer_cast<ArbitraryNativeConstantForCSTValue>(constant);

		lassert(c);

		SerializedObjectFlattener flattener;

		return flattener.flatten(
			std::make_pair(
				c->mValue,
				c->mAsImplval
				)
			)->toString();
		}

	static ArbitraryNativeConstantTypeRegistrar<ArbitraryNativeConstantForCSTValueType> sRegistrar;
};

ArbitraryNativeConstantTypeRegistrar<ArbitraryNativeConstantForCSTValueType>
	ArbitraryNativeConstantForCSTValueType::sRegistrar;




ArbitraryNativeConstantForCSTValue::ArbitraryNativeConstantForCSTValue(
														const CSTValue& in,
														bool asImplval) :
											mValue(in),
											mAsImplval(asImplval)
	{
	mReference = mValue.getReference();
	}

ArbitraryNativeConstantType* ArbitraryNativeConstantForCSTValue::type()
	{
	return ArbitraryNativeConstantForCSTValueType::sRegistrar.typePtr();
	}

NativeType ArbitraryNativeConstantForCSTValue::nativeType()
	{
	if (mAsImplval)
		return nativeTypeForImplVal();
	else
		return nativeLayoutType(mValue.type());
	}

void* ArbitraryNativeConstantForCSTValue::pointerToData()
	{
	if (mAsImplval)
		return &mReference;
	else
		return mReference.data();
	}

std::string ArbitraryNativeConstantForCSTValue::description()
	{
	if (mAsImplval)
		return "ImplValContainer(" + prettyPrintString(mValue) + ")";
	else
		return "TypedValue(type=" + prettyPrintString(mValue.type()) +
			",data=" + prettyPrintString(mValue) + ")";
	}

hash_type ArbitraryNativeConstantForCSTValue::hash()
	{
	return hash_type(mAsImplval ? 1 : 0) + mValue.hash();
	}

NativeExpression ArbitraryNativeConstantForCSTValue::expressionForCSTValueTyped(const CSTValue& in)
	{
	return NativeExpression::Constant(
		NativeConstant::ArbitraryConstant(
			boost::shared_ptr<ArbitraryNativeConstant>(
				new ArbitraryNativeConstantForCSTValue(in, false)
				)
			)
		);
	}

NativeExpression ArbitraryNativeConstantForCSTValue::expressionForCSTValueAsImplval(const CSTValue& in)
	{
	return NativeExpression::Constant(
		NativeConstant::ArbitraryConstant(
			boost::shared_ptr<ArbitraryNativeConstant>(
				new ArbitraryNativeConstantForCSTValue(in, true)
				)
			)
		);
	}

}
}

