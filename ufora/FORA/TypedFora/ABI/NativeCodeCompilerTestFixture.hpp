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

#include "../../Runtime.hppml"
#include "../../Native/NativeCode.hppml"
#include "../../Native/TypedNativeExpression.hppml"
#include "../../Native/TypedNativeLibraryFunction.hpp"
#include "../../../core/UnitTest.hpp"
#include "../../../core/UnitTestCppml.hpp"
#include "../../../core/Logging.hpp"
#include "../JitCompiler/TypedNativeFunctionPointer.hpp"
#include "NativeLayoutType.hppml"

namespace TypedFora {
namespace Abi {

class NativeCodeCompilerTestFixture {
public:
	NativeCodeCompilerTestFixture() :
			compiler(Runtime::getRuntime().getTypedForaCompiler())
		{
		lassert(compiler);
		}

	template<class R>
	TypedNativeFunctionPointer<R (*)()> compile(
				TypedNativeExpression<R> fp()
				)
		{
		return TypedNativeFunctionPointer<R (*)()>(compiler,
			[&]()
				{
				return fp().getExpression();
				}
			);
		}

	template<class R, class A1>
	TypedNativeFunctionPointer<R (*)(A1)> compile(
				TypedNativeExpression<R> fp(
						TypedNativeExpression<A1>
						)
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1)>(compiler,
			[&](	const NativeExpression& a1)
				{
				return fp(
					TypedNativeExpression<A1>(a1)
					).getExpression();
				}
			);
		}

	template<class R, class A1, class A2>
	TypedNativeFunctionPointer<R (*)(A1, A2)> compile(
				TypedNativeExpression<R> fp(
						TypedNativeExpression<A1>,
						TypedNativeExpression<A2>
						)
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1, A2)>(compiler,
			[&](	const NativeExpression& a1,
					const NativeExpression& a2)
				{
				return fp(
					TypedNativeExpression<A1>(a1),
					TypedNativeExpression<A2>(a2)
					).getExpression();
				}
			);
		}

	template<class R, class A1, class A2, class A3>
	TypedNativeFunctionPointer<R (*)(A1, A2, A3)> compile(
				TypedNativeExpression<R> fp(
						TypedNativeExpression<A1>,
						TypedNativeExpression<A2>,
						TypedNativeExpression<A3>
						)
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1, A2, A3)>(compiler,
			[&](	const NativeExpression& a1,
					const NativeExpression& a2,
					const NativeExpression& a3)
				{
				return fp(
					TypedNativeExpression<A1>(a1),
					TypedNativeExpression<A2>(a2),
					TypedNativeExpression<A3>(a3)
					).getExpression();
				}
			);
		}


	template<class R, class A1>
	TypedNativeFunctionPointer<R (*)(A1)> compile(
				TypedNativeExpression<R> (TypedNativeExpression<A1>::*fp)() const
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1)>(compiler,
			[&](const NativeExpression& in) {
				return (TypedNativeExpression<A1>(in).*fp)().getExpression();
				}
			);
		}

	template<class R, class A1>
	TypedNativeFunctionPointer<R (*)(A1)> compile(
				TypedNativeExpression<R> (TypedNativeExpressionBehaviors<A1>::*fp)() const
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1)>(compiler,
			[&](const NativeExpression& in) {
				return (TypedNativeExpression<A1>(in).*fp)().getExpression();
				}
			);
		}

	template<class R, class A1, class A2>
	TypedNativeFunctionPointer<R (*)(A1, A2)> compile(
				TypedNativeExpression<R> (TypedNativeExpression<A1>::*fp)(
						TypedNativeExpression<A2>
						) const
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1, A2)>(compiler,
			[&](	const NativeExpression& in,
					const NativeExpression& a2
					) {
				return (TypedNativeExpression<A1>(in).*fp)(
						TypedNativeExpression<A2>(a2)
						).getExpression();
				}
			);
		}

	template<class R, class A1, class A2>
	TypedNativeFunctionPointer<R (*)(A1, A2)> compile(
				TypedNativeExpression<R> (TypedNativeExpressionBehaviors<A1>::*fp)(
						TypedNativeExpression<A2>
						) const
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1, A2)>(compiler,
			[&](	const NativeExpression& in,
					const NativeExpression& a2
					) {
				return (TypedNativeExpression<A1>(in).*fp)(
						TypedNativeExpression<A2>(a2)
						).getExpression();
				}
			);
		}

	template<class R, class A1, class A2, class A3>
	TypedNativeFunctionPointer<R (*)(A1, A2, A3)> compile(
				TypedNativeExpression<R> (TypedNativeExpression<A1>::*fp)(
						TypedNativeExpression<A2>,
						TypedNativeExpression<A3>
						) const
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1, A2, A3)>(compiler,
			[&](	const NativeExpression& in,
					const NativeExpression& a2,
					const NativeExpression& a3
					) {
				return (TypedNativeExpression<A1>(in).*fp)(
						TypedNativeExpression<A2>(a2),
						TypedNativeExpression<A3>(a3)
						).getExpression();
				}
			);
		}

	template<class R, class A1, class A2, class A3>
	TypedNativeFunctionPointer<R (*)(A1,A2,A3)> compile(
				TypedNativeExpression<R> (TypedNativeExpressionBehaviors<A1>::*fp)(
						TypedNativeExpression<A2>,
						TypedNativeExpression<A3>
						) const
				)
		{
		return TypedNativeFunctionPointer<R (*)(A1, A2, A3)>(compiler,
			[&](	const NativeExpression& in,
					const NativeExpression& a2,
					const NativeExpression& a3
					) {
				return (TypedNativeExpression<A1>(in).*fp)(
						TypedNativeExpression<A2>(a2),
						TypedNativeExpression<A3>(a3)
						).getExpression();
				}
			);
		}

	template<class R, class A1>
	R callLibraryFunction(R (*funPtr)(A1), A1 a1)
		{
		TypedNativeFunctionPointer<R (*)(A1)> fun(
			compiler,
			[&](NativeExpression a1E) {
				return makeTypedNativeLibraryFunction(funPtr)(
					TypedNativeExpression<A1>(a1E)
					).getExpression();
				}
			);

		return fun(a1);
		}

	template<class R, class A1, class A2>
	R callLibraryFunction(R (*funPtr)(A1, A2), A1 a1, A2 a2)
		{
		TypedNativeFunctionPointer<R (*)(A1, A2)> fun(
			compiler,
			[&](NativeExpression a1E, NativeExpression a2E) {
				return makeTypedNativeLibraryFunction(funPtr)(
					TypedNativeExpression<A1>(a1E),
					TypedNativeExpression<A2>(a2E)
					).getExpression();
				}
			);

		return fun(a1, a2);
		}

	PolymorphicSharedPtr<TypedFora::Compiler> compiler;
};

}
}

