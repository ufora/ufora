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

//wrapper around a raw function pointer representing a piece of compiled
//llvm code. such a function may only be accessed or called by invocation
//of the TypedFora::Compiler
class NativeFunctionPointer {
public:
	explicit NativeFunctionPointer(void* inJumpPtr)
		{
		mJumpPtr = inJumpPtr;
		}
	NativeFunctionPointer() : mJumpPtr(0)
		{
		}
	NativeFunctionPointer(const NativeFunctionPointer& in) :
			mJumpPtr(in.mJumpPtr)
		{
		}
	
	NativeFunctionPointer& operator=(const NativeFunctionPointer& in)
		{
		mJumpPtr = in.mJumpPtr;
		return *this;
		}
	
	bool isEmpty() const
		{
		return mJumpPtr == 0;
		}

	bool	operator<(const NativeFunctionPointer& in) const
		{
		return mJumpPtr < in.mJumpPtr;
		}
	bool	operator==(const NativeFunctionPointer& in) const
		{
		return mJumpPtr == in.mJumpPtr;
		}
	bool	operator!=(const NativeFunctionPointer& in) const
		{
		return mJumpPtr != in.mJumpPtr;
		}

	void* extractRawJumpPointer(void) const
		{
		return mJumpPtr;
		}
private:
	void*	mJumpPtr;		
};

