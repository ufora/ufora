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
#include "../TypedFora/ABI/VectorHandle.hpp"
#include "../TypedFora/ABI/BigVectorLayouts.hppml"
#include "VectorUtilities.hpp"
#include "../../core/math/RandomHashGenerator.hpp"
#include "../Core/ExecutionContext.hppml"
#include "../Core/ValueDeepcopier.hppml"
#include "../VectorDataManager/VectorDataManager.hppml"
#include "../Judgment/JudgmentOnValue.hppml"
#include "../Core/ImplValContainer.hppml"
#include "../Core/MemoryPool.hpp"
#include "../Core/ImplValContainerUtilities.hppml"

using TypedFora::Abi::VectorHandle;

using TypedFora::Abi::VectorRecord;

using TypedFora::Abi::BigVectorPageLayout;

using TypedFora::Abi::VectorDataIDSlice;

ImplValContainer    createFORAVector(
						const JudgmentOnResult& elementJOR,
						const VectorDataID& inID,
						uword_t nElements,
						uint64_t bytecount,
						MemoryPool* inPool,
						VectorDataManager* inVDM
						)
	{
	if (nElements == 0)
		return ImplValContainerUtilities::createVector(VectorRecord());

	BigVectorPageLayout layout(inID, nElements, elementJOR, inVDM->newVectorHash());

	inVDM->getBigVectorLayouts()->registerNewLayout(layout);

	VectorHandle* dataPtr =
		inPool->construct<VectorHandle>(
			layout.identity(),
			Fora::PageletTreePtr(),
			(TypedFora::Abi::ForaValueArray*)0,
			inPool,
			inVDM->newVectorHash()
			);

	return ImplValContainerUtilities::createVector(
		VectorRecord(dataPtr)
		);
	}

ImplValContainer    createFORAVector(
						const JudgmentOnResult& elementJOR,
						const ImmutableTreeVector<VectorDataIDSlice>& inIDs,
						MemoryPool* inPool,
						VectorDataManager* inVDM
						)
	{
	BigVectorPageLayout layout(inIDs, elementJOR, hashValue(inIDs));

	inVDM->getBigVectorLayouts()->registerNewLayout(layout);

	VectorHandle* dataPtr =
		inPool->construct<VectorHandle>(
			layout.identity(),
			Fora::PageletTreePtr(),
			(TypedFora::Abi::ForaValueArray*)0,
			inPool,
			hashValue(inIDs)
			);

	return ImplValContainerUtilities::createVector(
		VectorRecord(dataPtr)
		);
	}

ImplValContainer    createFORAVector(
						const JOV& elementJOV,
						const VectorDataID& inID,
						uword_t nElements,
						uint64_t bytecount,
						MemoryPool* inPool,
						VectorDataManager* inVDM
						)
	{
	return createFORAVector(
		JudgmentOnResult(elementJOV),
		inID,
		nElements,
		bytecount,
		inPool,
		inVDM
		);
	}

ImplValContainer    createFORAFreeBinaryVector(
						const VectorDataID& inID,
						uword_t nElements,
						MemoryPool* inPool,
						VectorDataManager* inVDM
						)
	{
	return createFORAVector(
		JOV::OfType(Type::Integer(8, false)),
		inID,
		nElements,
		nElements,
		inPool,
		inVDM
		);
	}

ImplValContainer    createFORAFreeBinaryVectorFromSlices(
						const ImmutableTreeVector<VectorDataIDSlice>& inIDs,
						MemoryPool* inPool,
						VectorDataManager* inVDM
						)
	{
	return createFORAVector(
		JudgmentOnResult(JOV::OfType(Type::Integer(8, false))),
		inIDs,
		inPool,
		inVDM
		);
	}

ImplValContainer    createFORAVector(
                        const ImmutableTreeVector<ImplValContainer>& elements,
						MemoryPool* inPool,
						hash_type vectorHash
						)
	{
	if (elements.size() == 0)
		return ImplValContainerUtilities::createVector(VectorRecord());

	lassert(inPool);

	VectorRecord vec;

	if (!elements.size())
		ImplValContainerUtilities::createVector(VectorRecord());

	TypedFora::Abi::ForaValueArray* array =
		TypedFora::Abi::ForaValueArray::Empty(inPool);

	ValueDeepcopierState extractorState;

	ValueDeepcopier duplicator(extractorState, true, inPool, false, false);

	for (long k = 0; k < elements.size();k++)
		array->append(duplicator.duplicate(elements[k]));

	VectorRecord vector(
		inPool->construct<VectorHandle>(
			Fora::BigVectorId(),
			Fora::PageletTreePtr(),
			array,
			inPool,
			vectorHash
			)
		);

	return ImplValContainerUtilities::createVector(vector);
	}


