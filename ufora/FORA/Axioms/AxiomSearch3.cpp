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
#include "AxiomSearch.hppml"
#include "../Judgment/JudgmentOnValue.hppml"
#include "../Judgment/JudgmentOnValueTree.hppml"

namespace Fora {

Nullable<uword_t> lookupAgainstRule(
						const JudgmentOnValueTuple& vals,
						const JudgmentOnValueTreeBinaryRule& rule,
						const std::set<uword_t>& commonSubIndices,
						long indexIfTrue, 
						long indexIfFalse
						)
	{
	Nullable<bool> matches = rule.covers(vals);

	if (matches)
		return Fora::searchJOVTree(vals, *matches ? indexIfTrue : indexIfFalse);

	//check if we can short-circuit
	if (commonSubIndices.size() == 0)
		return null();

	Nullable<uword_t> fromTrue = Fora::searchJOVTree(vals, indexIfTrue);

	if (!fromTrue || commonSubIndices.find(*fromTrue) == commonSubIndices.end())
		return null();

	Nullable<uword_t> fromFalse = Fora::searchJOVTree(vals, indexIfFalse);

	if (!fromFalse || fromFalse != fromTrue || 
				commonSubIndices.find(*fromFalse) == commonSubIndices.end())
		return null();

	return fromFalse;
	}

}

