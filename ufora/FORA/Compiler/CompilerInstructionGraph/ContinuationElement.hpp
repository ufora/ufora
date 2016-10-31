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

#include "../../ControlFlowGraph/ControlFlowGraph.hppml"
#include "../../Interpreter/ContinuationArgs.hppml"
#include "InstructionPtr.hpp"

namespace Fora {
namespace Compiler {
namespace CompilerInstructionGraph {

class Continuation;
class Instruction;

typedef Fora::Interpreter::ContinuationArgs ContinuationArgs;

//represents a continuation conditional on typing (e.g. a single exit flow)
//these objects should never be held by the interpreter, and may change frequently
class ContinuationElement {
	ContinuationElement();
	ContinuationElement(const ContinuationElement& in);
	ContinuationElement& operator=(const ContinuationElement& in);

	ContinuationElement(
		Continuation* cont,
		const JudgmentOnValue& filter,
		const ControlFlowGraph* targetGraph,
		const Nullable<string>& targetLabel,
		const ContinuationArgs& args
		);

	friend class Instruction;
	friend class Continuation;

	//remove "this" and put in mContinuationPtr->mOldContinuationElements
	void destroy(ContinuationElement* inPrevious);

	//reattach the continuation to the appropriate instruction
	bool recomputeTarget();

public:
	Continuation* getContinuationPtr(void) const;

	InstructionPtr getSourceInstructionPtr(void) const;

	InstructionPtr getTargetInstructionPtr(void) const;

	const JudgmentOnValue& getFilter(void) const;

	const ContinuationArgs&	getContinuationArgs(void) const;

	string toString(void) const;
	ContinuationElement* nextContinuationElementPtr(void);

	bool isDestroyed(void) const;

	uint64_t executionCount(void);

	const ImmutableTreeVector<JudgmentOnValue>& getTargetJOVs() const
		{
		return mTargetJOVs;
		}

private:
	bool mIsDestroyed;

	ContinuationElement* mNextContinuationElementPtr;

	Continuation* mContinuationPtr;

	InstructionPtr mSourceInstructionPtr;

	InstructionPtr mTargetInstructionPtr;

	ContinuationArgs mContinuationArgs;

	JudgmentOnValue	mFilter;

	ImmutableTreeVector<JudgmentOnValue> mTargetJOVs;
};

}
}
}

