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

#include "CallFrame.hpp"
#include "EvalFrameArgList.hpp"

using std::vector;

class StackFrameAllocator;

namespace TypedFora {

class MetadataInstruction;

}

class ControlFlowGraph;

namespace Fora {
namespace Interpreter {

class EvalFrame {
public:
	CallFrame callFrame;

	InstructionPtr instructionPtr;

	ImplVal	resultValue;

	uint64_t uniqueId;

	static uint64_t allocateNewUniqueEvalFrameID();

	//if we were ever a machine code term, what were we, and how many instructions ago?
	pair<TypedFora::MetadataInstruction, long>* wasEverMachineCodeFrame;

	EvalFrameArgList& evalFrameArgList();

	static EvalFrame* allocate(
						const ControlFlowGraph& controlFlowGraph,
						Nullable<string> label,
						StackFrameAllocator& executionContext,
						uint64_t inUniqueId,
						const Nullable<TypedFora::MetadataInstruction>& inWasEverMachineCodeFrame
						);

	static void free(EvalFrame* frame, StackFrameAllocator& allocator);

	void copyApplyArgsIntoArgSlots(const Fora::ApplyArgFrame& args, RefcountPool* inPool);

	void copyPooledImplValsIntoFrame(const vector<ImplVal>& args);

	void unpackUnownedTupleIntoPooledArguments(ImplVal tupleImplVal, RefcountPool* inPool);

	void addImplvalsToRefcountPool(RefcountPool* inPool);

	uword_t size() const;

	void setInstructionPtr(InstructionPtr newInstructionPtr);

private:
	EvalFrameArgList* mEvalFrameArgList;
};

}
}

