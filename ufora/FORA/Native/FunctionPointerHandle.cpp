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
#include "FunctionPointerHandle.hpp"

#include "../../core/lassert.hpp"
#include <boost/make_shared.hpp>

using namespace std;

FunctionPointerArray::FunctionPointerArray(size_t inSize)
		: mArrayBase(0), mSize(inSize)
	{
	}

bool FunctionPointerArray::isEmpty() const
	{
	return mArrayBase == 0;
	}

void FunctionPointerArray::fillArray(
				const std::vector<NativeFunctionPointerAndEntrypointId>&	inPointers
				)
	{
	lassert(!mArrayBase);
	lassert(mSize == inPointers.size());

	NativeFunctionPointerAndEntrypointId* base = new NativeFunctionPointerAndEntrypointId[mSize];

	for (long k = 0; k < mSize;k++)
		base[k] = inPointers[k];

	//now that everything is set, do the copy. other clients will immediately
	//see all the values in the system
	mArrayBase = base;
	}

FunctionPointerHandle	FunctionPointerArray::getHandle(size_t inIndex)
	{
	lassert(inIndex < mSize);
	return FunctionPointerHandle(this, inIndex);
	}

NativeFunctionPointerAndEntrypointId FunctionPointerArray::get(size_t ix) const
	{
	if (!mArrayBase)
		return NativeFunctionPointerAndEntrypointId();

	lassert(ix < mSize);

	return mArrayBase[ix];
	}

FunctionPointerHandle::FunctionPointerHandle(
							FunctionPointerArray* inArray, uint32_t inIndex)
		: mArray(inArray), mIndex(inIndex)
	{
	}

FunctionPointerArray*	FunctionPointerHandle::getArray()
	{
	return mArray;
	}

NativeFunctionPointerAndEntrypointId FunctionPointerHandle::get() const
	{
	lassert(mArray);
	return mArray->get(mIndex);
	}

size_t				FunctionPointerHandle::getIndex(void) const
	{
	return mIndex;
	}

void FunctionPointerHandle::update(NativeFunctionPointerAndEntrypointId inNewValue)
	{
	lassert(mArray);
	lassert(!mArray->isEmpty());
	mArray->mArrayBase[mIndex] = inNewValue;
	}

pair<NativeFunctionPointerAndEntrypointId**, uint32_t>
									FunctionPointerHandle::getAddrAndOffset() const
	{
	lassert(mArray);
	return make_pair(&mArray->mArrayBase, mIndex);
	}

bool FunctionPointerHandle::operator==(const FunctionPointerHandle& other) const
	{
	return mArray == other.mArray && mIndex == other.mIndex;
	}

bool FunctionPointerHandle::operator!=(const FunctionPointerHandle& other) const
	{
	return !(*this == other);
	}

bool FunctionPointerHandle::isEmpty() const
	{
	return !mArray || mArray->isEmpty();
	}

