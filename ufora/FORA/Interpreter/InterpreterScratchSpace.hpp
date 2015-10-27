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

#include <vector>
#include "../../core/Common.hppml"
#include "../Core/Type.hppml"
#include "../Core/ApplyArgFrame.hppml"

using std::vector;
using std::pair;

class ImplVal;
class Symbol;
template<class T>
class Nullable;

namespace Fora {

class ApplyArgFrame;

}

namespace Fora {
namespace Interpreter {

class EvalFrameArgList;

class InterpreterScratchSpace {
public:
	ImplVal& getImplval(uword_t ix);
	
	const ImplVal& getImplval(uword_t ix) const;
	
	void push(ImplVal evalFrameArg);
	
	void clear();

	void loadAxiomSpilloverData(
			const Fora::ApplyArgFrame& values,
			uword_t offsetIntoValueList
			);
	
	void loadAxiomSpilloverData(const EvalFrameArgList& argList);

	const Type& getAxiomSpilloverType() const;

	char* getAxiomSpilloverData(); 

	Fora::ApplyArgFrame argumentPackingTempStorage;

private:
	vector<ImplVal> mImplvals;

	vector<char> mAxiomSpilloverData;

	Type mAxiomSpilloverType;
};

}
}

