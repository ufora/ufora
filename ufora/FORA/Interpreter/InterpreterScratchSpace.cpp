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
#include "InterpreterScratchSpace.hpp"
#include "EvalFrameArgList.hpp"
#include "../Core/ApplyArgFrame.hppml"
#include "../Core/ImplVal.hppml"
#include "../../core/Logging.hpp"

namespace Fora {
namespace Interpreter {

ImplVal& InterpreterScratchSpace::getImplval(uword_t ix)
	{
	lassert(ix < mImplvals.size());
	return mImplvals[ix];
	}

const ImplVal& InterpreterScratchSpace::getImplval(uword_t ix) const
	{
	lassert(ix < mImplvals.size());
	return mImplvals[ix];
	}

void InterpreterScratchSpace::push(ImplVal implval)
	{
	mImplvals.push_back(implval);
	}

void InterpreterScratchSpace::clear()
	{
	mImplvals.clear();
	}

void InterpreterScratchSpace::loadAxiomSpilloverData(
		const Fora::ApplyArgFrame& values,
		uword_t offsetIntoValueList
		)
	{
	uword_t nBytes = 0;
	for (long j = offsetIntoValueList; j < values.size(); j++)
		nBytes = nBytes + values[j].first.type().size();

	mAxiomSpilloverData.resize(nBytes + 1);
	char* dataPtr = &mAxiomSpilloverData[0];

	ImmutableTreeVector<Type> types;
	ImmutableTreeVector<Nullable<Symbol> > symbols;

	for (long j = offsetIntoValueList; j < values.size(); j++)
		{
		pair<ImplVal, Nullable<Symbol> > p = values[j];

		memcpy(dataPtr, p.first.data(), p.first.type().size());
		types = types + p.first.type();
		symbols = symbols + p.second;

		dataPtr += p.first.type().size();
		}

	mAxiomSpilloverType = Type::Tuple(types, symbols);
	}

void InterpreterScratchSpace::loadAxiomSpilloverData(const EvalFrameArgList& argList)
	{
	mAxiomSpilloverData.resize((argList.size() + 1) * sizeof(ImplVal));
	ImplVal* dataPtr = (ImplVal*)&mAxiomSpilloverData[0];

	ImmutableTreeVector<Type> types;

	for (uword_t j = 0; j < argList.size(); j++)
		{
		dataPtr[j] = argList[j];
		types = types + argList[j].type();
		}

	mAxiomSpilloverType = Type::UnnamedTuple(types);
	}

const Type& InterpreterScratchSpace::getAxiomSpilloverType() const
	{
	return mAxiomSpilloverType;
	}

char* InterpreterScratchSpace::getAxiomSpilloverData()
	{
	return &mAxiomSpilloverData[0];
	}

}
}
