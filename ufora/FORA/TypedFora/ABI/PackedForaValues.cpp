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
#include "PackedForaValues.hppml"
#include "../../Core/ImplValContainer.hppml"
#include "../../../core/Logging.hpp"

using namespace TypedFora::Abi;

void PackedForaValues::destroy()
	{
	if (elementJOV().type())
		elementJOV().type()->destroy(data(), count(), stride());
	else
		{
		for (long k = 0; k < count(); k++)
			pointerToElement<ImplValContainer>(k)->~ImplValContainer();
		}
	}

void PackedForaValues::initialize(PackedForaValues otherValues)
	{
	initialize(*this, otherValues);
	}

void PackedForaValues::initialize(PackedForaValues target, PackedForaValues source)
	{
	lassert(target.count() == source.count());
	lassert(target.elementJOV() == source.elementJOV());

	lassert_dump(target.stride() >= strideFor(target.elementJOV()) || target.count() == 1,
		"Stride for " << prettyPrintString(target.elementJOV()) << " is "
			<< strideFor(target.elementJOV())
			<< " which is not less than target stride "
			<< target.stride()
		);

	lassert_dump(source.stride() >= strideFor(source.elementJOV()) || target.count() == 1,
		"Stride for " << prettyPrintString(source.elementJOV()) << " is "
			<< strideFor(source.elementJOV())
			<< " which is not less than source stride "
			<< source.stride()
		);

	if (target.elementJOV().type())
		target.elementJOV().type()->initialize(
			target.data(),
			source.data(),
			target.count(),
			target.stride(),
			source.stride()
			);
	else
		{
		for (long k = 0; k < target.count(); k++)
			new (target.pointerToElement<ImplValContainer>(k))
				ImplValContainer(*source.pointerToElement<ImplValContainer>(k));
		}
	}

size_t PackedForaValues::strideFor(JudgmentOnValue jmt)
	{
	if (jmt.type())
		return jmt.type()->size();

	return sizeof(ImplValContainer);
	}
