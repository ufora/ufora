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
#include "ContinuationElement.hpp"
#include "Instruction.hppml"
#include "InstructionGraph.hppml"
#include "../../../core/Logging.hpp"

namespace Fora {
namespace Compiler {
namespace CompilerInstructionGraph {

Continuation* ContinuationElement::getContinuationPtr(void) const
	{
	return mContinuationPtr;
	}

InstructionPtr ContinuationElement::getSourceInstructionPtr(void) const
	{
	return mSourceInstructionPtr;
	}

InstructionPtr ContinuationElement::getTargetInstructionPtr(void) const
	{
	return mTargetInstructionPtr;
	}

const JudgmentOnValue& ContinuationElement::getFilter(void) const
	{
	return mFilter;
	}

const ContinuationArgs&	ContinuationElement::getContinuationArgs(void) const
	{
	return mContinuationArgs;
	}

ContinuationElement* ContinuationElement::nextContinuationElementPtr(void)
	{
	return mNextContinuationElementPtr;
	}
				
bool ContinuationElement::isDestroyed(void) const
	{
	return mIsDestroyed;
	}

uint64_t ContinuationElement::executionCount(void)
	{
	return 0;
	}

ContinuationElement::ContinuationElement() 
	{
	}
					
ContinuationElement::ContinuationElement(const ContinuationElement& in) 
	{
	}
					
ContinuationElement& ContinuationElement::operator=(const ContinuationElement& in)
	{
	return *this;
	}
						
ContinuationElement::ContinuationElement(
						Continuation* continuationPtr,
						const JudgmentOnValue& filter,
						const ControlFlowGraph* targetControlFlowGraph,
						const Nullable<string>& targetLabel,
						const ContinuationArgs& continuationArgs
						)
	{
	//create outselves and add into our parent's linked list.
	//Be careful - the interpreter could read right into us!
	mIsDestroyed = false;

	mTargetJOVs = 
			continuationArgs.targetJOV(
				continuationPtr->getSourceInstruction()->jovs(),
				filter
				);
	
	mSourceInstructionPtr = continuationPtr->getSourceInstruction();
	
	InstructionGraph* instructionGraphPtr = &mSourceInstructionPtr->instructionGraph();

	if (mSourceInstructionPtr->isRootInstruction())
		{
		mTargetInstructionPtr = 
			instructionGraphPtr->getRootInstruction(
				*targetControlFlowGraph,
				targetLabel
				);
		lassert(mTargetInstructionPtr->isRootInstruction());
		}
	else
		{
		mTargetInstructionPtr = 
			instructionGraphPtr->getInstruction(
				*targetControlFlowGraph,
				targetLabel,
				mTargetJOVs
				);
		}

	mTargetInstructionPtr->addIncomingContinuationElement(this);

	instructionGraphPtr->onInstructionContinuationsChanged(mSourceInstructionPtr);

	mContinuationPtr = continuationPtr;
	mFilter = filter;
	mContinuationArgs = continuationArgs;
	mNextContinuationElementPtr = 0;

    mContinuationPtr->insertContinuationElement(this, mFilter);
	}

bool ContinuationElement::recomputeTarget()
	{
	if (mSourceInstructionPtr->isRootInstruction())
		return false;

	lassert(!mIsDestroyed);
	
	InstructionPtr newTargetInstruction =
		mTargetInstructionPtr->instructionGraph().getInstruction(
			mTargetInstructionPtr->getGraph(),
			mTargetInstructionPtr->getLabel(),
			mTargetJOVs
			);

	if (newTargetInstruction == mTargetInstructionPtr)
		return false;

	mTargetInstructionPtr->dropIncomingContinuationElement(this);
	mTargetInstructionPtr = newTargetInstruction;
	mTargetInstructionPtr->addIncomingContinuationElement(this);

	mTargetInstructionPtr->instructionGraph().onInstructionContinuationsChanged(mSourceInstructionPtr);
	
	return true;
	}
    
string ContinuationElement::toString(void) const
	{
	if (mContinuationPtr->mRequiresResult)
		return "[" + prettyPrintString(mFilter) + "] -> "
			 + prettyPrintString(mTargetInstructionPtr->toString(true));
	else
		return " -> " + prettyPrintString(mTargetInstructionPtr->toString(true));
	}

void ContinuationElement::destroy(ContinuationElement* prev)
	{
	lassert_dump(!mIsDestroyed, "double destroy!");
	mIsDestroyed = true;

	//first, remove from the linked list
	if (prev == 0)
		mContinuationPtr->mFirstContinuationElementPtr = mNextContinuationElementPtr;
	else
		prev->mNextContinuationElementPtr = mNextContinuationElementPtr;

	mTargetInstructionPtr->dropIncomingContinuationElement(this);

	ContinuationElement* continuationElementPtr = mContinuationPtr->mFirstContinuationElementPtr;
	while (continuationElementPtr)
		{
		lassert(continuationElementPtr != this);
		continuationElementPtr = continuationElementPtr-> mNextContinuationElementPtr;
		}
	}
	
}
}
}

