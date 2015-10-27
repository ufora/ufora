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
#include <vector>
#include "../../core/cppml/CPPMLPrettyPrinter.hppml"
#include "NativeFunctionPointer.hpp"
#include "NativeFunctionPointerAndEntrypointId.hppml"
#include <stdint.h>

//forward declaration so that FunctionPointerArray can have FunctionPointerHandle
//as a friend

class FunctionPointerHandle;

class FunctionPointerArray {
		
		friend class FunctionPointerHandle;
		
		NativeFunctionPointerAndEntrypointId* mArrayBase;

		size_t mSize;

public:
		FunctionPointerArray(size_t inSize);
		
		//has the array been filled?
		bool isEmpty() const;
		
		size_t size() const { return mSize; }
		
		//fill the array with the given pointers
		//undefined if the array has been filled before
		//or if inPointers.size() is not equal to mSize
		//inPointers should never by empty
		void fillArray(const std::vector<NativeFunctionPointerAndEntrypointId>& inPointers);
		
		//if the array has been filled, then what's the pointer?
		//guaranteed not to be null if the array is filled
		//behaviour is undefined if the array is empty
		NativeFunctionPointerAndEntrypointId get(size_t inIndex) const;
		
		//gets the handle associated with inIndex
		FunctionPointerHandle getHandle(size_t inIndex);
};

/*************
A handle to a place where a NativeFunctionPointer can be placed.  This allows the
TypedFora::Compiler to swap new definitions of functions in for old ones.
*************/
class FunctionPointerHandle {
private:
		//pointer to a pointer to an array of native function pointers
		//we have to be able to make a whole group of NativeFunctionPointer
		//objects "go live" since they might refer to each other
		
		//essentially, "mPtr" is never zero. at initialization time, it points
		//to a NativeFunctionPointer* which is zero.
		//as soon as that is not zero, then this slot object should resolve to
		//	mPtr[0][mIndex]
		//
		FunctionPointerArray* mArray;
		
		//which function pointer in the table we point to
		uint32_t mIndex;
		
		friend class FunctionPointerArray;
		
		FunctionPointerHandle(FunctionPointerArray* inArray, uint32_t inIndex);
public:
		//creates a FunctionPointerHandle that can never be set or manipulated
		//in any way.
		FunctionPointerHandle() :
				mArray(0),
				mIndex(0)
			{
			}
		
		//Use the default destructor.
		//Use the default copy constructor and operator=.
		
		//Returns the function pointer.
		//if the array is not filled, this will be the empty NativeFunctionPointer
		NativeFunctionPointerAndEntrypointId get() const;
		
		size_t getIndex(void) const;
		
		FunctionPointerArray* getArray();
		
		//if the value isn't empty, then we can update it
		void	update(NativeFunctionPointerAndEntrypointId in);
		
		//Should this be const?  Rather, is there a safe way of making it const?
		std::pair<NativeFunctionPointerAndEntrypointId**, uint32_t> getAddrAndOffset() const;

		bool operator==(const FunctionPointerHandle& other) const;
		
		bool operator!=(const FunctionPointerHandle& other) const;
		
		bool isEmpty() const;
};

template<>
class CPPMLPrettyPrint<FunctionPointerHandle> {
public:
		static void prettyPrint(CPPMLPrettyPrintStream& s, const FunctionPointerHandle& t)
			{
			s << "FunctionPointerHandle(array=" << (void*)t.getAddrAndOffset().first
			  << ",ix=" << t.getAddrAndOffset().second << ")";
			}
};

