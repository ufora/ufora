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

#include "../../core/IntegerTypes.hpp"
class Type;

uword_t alignedOffset(const Type& t, uword_t unalignedOffset);

void copyBetweenAlignedAndPacked(
						bool copyFromAlignedToPacked,
						const Type& typ,
						uint8_t* alignedData,
						uint8_t* packedData
						);

void copyAlignedToPacked(const Type& typ, uint8_t* alignedData, uint8_t* packedData);

void copyPackedToAligned(const Type& typ, uint8_t* packedData, uint8_t* alignedData);

