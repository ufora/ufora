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
#include "TypedNativeLibraryFunction.hpp"
#include "../../core/Logging.hpp"

namespace {

bool allAreTrue(ImmutableTreeVector<bool> values)
	{
	for (long k = 0; k < values.size();k++)
		if (!values[k])
			return false;
	return true;
	}

}

NativeExpression callLibraryFunctionContainingCPPTypes(
			NativeLibraryFunctionTarget target,
			NativeType resultType,
			bool resultTypeIsPOD,
			ImmutableTreeVector<NativeExpression> inArguments,
			ImmutableTreeVector<bool> inArgumentTypesArePOD
			)
	{
	if (!resultTypeIsPOD && resultType.isNothing())
		resultTypeIsPOD = true;
	//make sure all of our arguments have types
	for (long k = 0; k < inArguments.size();k++)
		if (!inArguments[k].type())
			{
			NativeExpression e;
			for (long j = 0; j <= k; j++)
				e = e >> inArguments[j];

			return e;
			}

	//OK, our return type is OK. For each argument that isn't POD, we need to place a copy of it
	//on the stack and pass that instead
	ImmutableTreeVector<bool> passByPtr;
	for (long k = 0; k < inArgumentTypesArePOD.size(); k++)
		if (!inArgumentTypesArePOD[k])
			passByPtr = passByPtr + true;
		else
			passByPtr = passByPtr + false;

	return NativeExpression::CallLibraryFunction(
		target,
		resultType,
		inArguments,
		passByPtr,
		!resultTypeIsPOD
		);
	}

