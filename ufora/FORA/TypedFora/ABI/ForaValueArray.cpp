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
#include "ForaValueArray.hppml"
#include "../../Core/ShareableMemoryBlock.hppml"
#include "../../Core/MemoryPool.hpp"
#include "../../Judgment/JudgmentOnValue.hppml"
#include "../../../core/Logging.hpp"
#include "../../../core/Clock.hpp"
#include "../../../core/cppml/MemoizedAlternativePointer.hppml"
#include "ForaValueArraySpaceRequirements.hppml"
#include "ForaValueArrayImpl.hppml"
#include <boost/unordered_set.hpp>

using namespace TypedFora::Abi;

ForaValueArray::ForaValueArray()
	{
	}

ForaValueArray* ForaValueArray::Empty(MemoryPool* inOwningMemoryPool)
	{
	return inOwningMemoryPool->construct<ForaValueArrayImpl>(inOwningMemoryPool);
	}

void CPPMLPrettyPrint<const TypedFora::Abi::ForaValueArray*>::prettyPrint(
							CPPMLPrettyPrintStream& s,
							const TypedFora::Abi::ForaValueArray* t
							)
	{
	if (!t)
		{
		s << "FVA(null)";
		return;
		}

	s << "FVA(" << (void*)t << ": " << t->size() << " x " << t->currentJor();
	s << (t->isHomogenous() ? ",homogenous" :"");
	s << (t->usingOffsetTable() ? ",offsetTable" :"");
	s << (t->isWriteable() ? ",writeable" :"");
	s << ")";
	}

