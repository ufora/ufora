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

#include "../../core/PolymorphicSharedPtr.hpp"

class MemoryPool;
class VectorDataManager;
class VectorDataID;
class JudgmentOnResult;

namespace TypedFora {
namespace Abi {

class VectorDataIDSlice;

}
}

ImplValContainer    createFORAFreeBinaryVector(
                        const VectorDataID& inID,
                        uword_t nElements,
                        MemoryPool* inOwningMemoryPool,
                        VectorDataManager* inVDM
                        );

ImplValContainer    createFORAFreeBinaryVectorFromSlices(
                        const ImmutableTreeVector<TypedFora::Abi::VectorDataIDSlice>& inIDs,
                        MemoryPool* inOwningMemoryPool,
                        VectorDataManager* inVDM
                        );

ImplValContainer    createFORAVector(
                        const JudgmentOnValue& elementJOV,
                        const VectorDataID& inID,
                        uword_t nElements,
                        uint64_t inByteCount,
                        MemoryPool* inOwningMemoryPool,
                        VectorDataManager* inVDM
                        );

ImplValContainer    createFORAVector(
                        const JudgmentOnResult& elementJOR,
                        const VectorDataID& inID,
                        uword_t nElements,
                        uint64_t inByteCount,
                        MemoryPool* inOwningMemoryPool,
                        VectorDataManager* inVDM
                        );

ImplValContainer    createFORAVector(
                        const ImmutableTreeVector<ImplValContainer>& elements,
                        MemoryPool* inOwningMemoryPool,
                        hash_type vectorHash
                        );

