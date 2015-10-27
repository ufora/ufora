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
#include "EvalFrame.hpp"
#include "Instruction.hppml"
#include "InstructionGraph.hppml"
#include "../TypedFora/TypedFora.hppml"

namespace Fora {
namespace Interpreter {

EvalFrame* EvalFrame::allocate(
				const ControlFlowGraph& controlFlowGraph,
				Nullable<string> label,
				MemBlockAllocator& allocator,
				uint64_t inUniqueId,
				const Nullable<TypedFora::MetadataInstruction>& inWasEverMachineCodeFrame
				)
	{
	InstructionPtr rootInstructionPtr =
		Runtime::getRuntime().getInstructionGraph()->getInstruction(controlFlowGraph, label);

	uword_t totalVals = controlFlowGraph.maxArgCount();

	EvalFrame* newEvalFramePtr = (EvalFrame*) allocator.allocate(sizeof(EvalFrame));

	new (newEvalFramePtr) EvalFrame();

	newEvalFramePtr->mEvalFrameArgList = EvalFrameArgList::allocate(
											totalVals,
											allocator
											);

	newEvalFramePtr->instructionPtr = rootInstructionPtr;

	newEvalFramePtr->uniqueId = inUniqueId;

	if (!inWasEverMachineCodeFrame)
		newEvalFramePtr->wasEverMachineCodeFrame = 0;
	else
		newEvalFramePtr->wasEverMachineCodeFrame = 
			new pair<TypedFora::MetadataInstruction, long>(
				TypedFora::MetadataInstruction(*inWasEverMachineCodeFrame),
				0
				);

	return newEvalFramePtr;
	}

void EvalFrame::setInstructionPtr(InstructionPtr newInstructionPtr)
	{
	instructionPtr = newInstructionPtr;

	if (wasEverMachineCodeFrame)
		wasEverMachineCodeFrame->second++;
	}

void EvalFrame::zeroOutUnusedContinuationArgs()
	{
	ImplVal nothing;

	for (auto index: instructionPtr->getVariablesUnusedInContinuations())
		(*mEvalFrameArgList)[index] = nothing;
	}

void EvalFrame::free(EvalFrame* frame, MemBlockAllocator& allocator)
	{
	EvalFrameArgList::free(frame->mEvalFrameArgList, allocator);
	allocator.free(frame);

	if (frame->wasEverMachineCodeFrame)
		delete frame->wasEverMachineCodeFrame;
	}

void EvalFrame::copyApplyArgsIntoArgSlots(const Fora::ApplyArgFrame& args, RefcountPool* pool)
	{
	mEvalFrameArgList->copyApplyArgsIntoArgSlots(args, pool);
	}

EvalFrameArgList& EvalFrame::evalFrameArgList()
	{
	return *mEvalFrameArgList;
	}

void EvalFrame::copyPooledImplValsIntoFrame(const vector<ImplVal>& args)
	{
	mEvalFrameArgList->copyPooledImplValsIntoFrame(args);
	}

void EvalFrame::unpackUnownedTupleIntoPooledArguments(ImplVal tupleImplVal, RefcountPool* inPool)
	{
	mEvalFrameArgList->unpackUnownedTupleIntoPooledArguments(tupleImplVal, inPool);
	}

uword_t EvalFrame::size() const
	{
	return instructionPtr->argCount();
	}

void EvalFrame::addImplvalsToRefcountPool(RefcountPool* inPool)
	{
	mEvalFrameArgList->addImplvalsToRefcountPool(inPool);
	}

}
}

