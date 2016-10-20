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
#include "BigVectorPageLayout.hppml"
#include "../../../core/Logging.hpp"

namespace TypedFora {
namespace Abi {

BigVectorPageLayout::BigVectorPageLayout(
							VectorDataIDSlice slice,
							JudgmentOnResult jor,
							hash_type inGuid
							)
	{
	vectorIdentities() = vectorIdentities() + slice;
	cumulativeSizes() = cumulativeSizes() + (int64_t)slice.size();
	cumulativeBytecounts() = cumulativeBytecounts() + (uint64_t)slice.vector().getPage().bytecount();
	identity() = Fora::BigVectorId(inGuid, slice.size(), jor);
	}

BigVectorPageLayout::BigVectorPageLayout(
							VectorDataID id,
							uint64_t count,
							JudgmentOnResult jor,
							hash_type inGuid
							)
	{
	vectorIdentities() = vectorIdentities() + VectorDataIDSlice(id, IntegerRange(0, count));
	cumulativeSizes() = cumulativeSizes() + (int64_t)count;
	cumulativeBytecounts() = cumulativeBytecounts() + (uint64_t)id.getPage().bytecount();
	identity() = Fora::BigVectorId(
		inGuid,
		count,
		jor
		);
	}

BigVectorPageLayout::BigVectorPageLayout(
							VectorDataID id,
							uint64_t count,
							JudgmentOnValue jov,
							hash_type inGuid
							)
	{
	vectorIdentities() = vectorIdentities() + VectorDataIDSlice(id, IntegerRange(0, count));
	cumulativeSizes() = cumulativeSizes() + (int64_t)count;
	cumulativeBytecounts() = cumulativeBytecounts() + (uint64_t)id.getPage().bytecount();
	identity() = Fora::BigVectorId(
		inGuid,
		count,
		JudgmentOnResult(jov)
		);
	}

BigVectorPageLayout::BigVectorPageLayout(
						ImmutableTreeVector<VectorDataIDSlice> slices,
						JudgmentOnResult inVectorJor,
						hash_type inGuid
						)
	{
	vectorIdentities() = slices;

	int64_t cumulativeOffset = 0;
	uint64_t cumulativeBytecount = 0;

	for (long k = 0; k < vectorIdentities().size(); k++)
		{
		cumulativeOffset += vectorIdentities()[k].size();
		cumulativeBytecount += vectorIdentities()[k].vector().getPage().bytecount();

		cumulativeSizes() = cumulativeSizes() + cumulativeOffset;
		cumulativeBytecounts() = cumulativeBytecounts() + cumulativeBytecount;
		}

	identity() = Fora::BigVectorId(
		inGuid,
		cumulativeOffset,
		inVectorJor
		);
	}

pair<VectorDataIDSlice, int64_t> BigVectorPageLayout::sliceAndOffsetContainingIndex(int64_t index) const
	{
	long sliceIx = sliceAtIndex(index);

	return make_pair(vectorIdentities()[sliceIx], startIndex(sliceIx));
	}

long BigVectorPageLayout::sliceAtIndex(int64_t index) const
	{
	lassert_dump(
		index >= 0 && index <= size(),
		"index " << index << " not in [0," << size() << "]"
		);

	long sliceContaining = cumulativeSizes().lowerBound(index);

	if (cumulativeSizes()[sliceContaining] == index)
		sliceContaining++;

	return sliceContaining;
	}

VectorDataID BigVectorPageLayout::vectorDataIdAtIndex(int64_t index) const
	{
	return vectorIdentities()[sliceAtIndex(index)].vector();
	}

Fora::PageId BigVectorPageLayout::pageAtIndex(int64_t index) const
	{
	return vectorDataIdAtIndex(index).getPage();
	}

namespace {

ImmutableTreeVector<VectorDataIDSlice> addIfNonempty(
										ImmutableTreeVector<VectorDataIDSlice> vec,
										VectorDataIDSlice slice
										)
	{
	if (slice.slice().size())
		return vec + slice;
	return vec;
	}

ImmutableTreeVector<pair<Fora::PageId, IntegerSequence> > addIfNonempty(
										ImmutableTreeVector<pair<Fora::PageId, IntegerSequence> > vec,
										pair<Fora::PageId, IntegerSequence> slice
										)
	{
	if (slice.second.size())
		return vec + slice;
	return vec;
	}

int64_t sliceContaining(ImmutableTreeSet<int64_t> cumulativeSizes, int64_t offset)
	{
	int64_t lb = cumulativeSizes.lowerBound(offset);

	if (lb >= cumulativeSizes.size())
		return cumulativeSizes.size() - 1;

	if (cumulativeSizes[lb] == offset)
		return lb + 1;

	return lb;
	}

}

ImmutableTreeVector<VectorDataIDSlice> BigVectorPageLayout::slicesCoveringRange(IntegerRange sequence) const
	{
	if (!sequence.size() || !cumulativeSizes().size())
		return emptyTreeVec();

	sequence = sequence.intersect(IntegerRange(0, size()));

	int64_t lowValue = sequence.low();
	int64_t highValue = sequence.high() - 1;

	int64_t sliceContainingLowValue = sliceContaining(cumulativeSizes(), lowValue);
	int64_t sliceContainingHighValue = sliceContaining(cumulativeSizes(), highValue);

	ImmutableTreeVector<VectorDataIDSlice> tr;

	for (long slice = sliceContainingLowValue;
				slice <= sliceContainingHighValue && slice < vectorIdentities().size(); slice++)
		{
		tr = addIfNonempty(
			tr,
			vectorIdentities()[slice].slice(sequence - startIndex(slice))
			);
		}

	uint64_t totalCt = 0;
	for (long k = 0; k < tr.size(); k++)
		totalCt += tr[k].slice().size();

	lassert_dump(
		totalCt == sequence.size(),
		totalCt << " != " << sequence.size() << ": "
			<< prettyPrintString(vectorIdentities())
			<< " -> "
			<< prettyPrintString(tr)
			<< " and "
			<< prettyPrintString(sequence)
			<< " over range " << sliceContainingLowValue << " to " << sliceContainingHighValue
			<< " which contain values " << lowValue << " and " << highValue
			<< ". cum sizes are " << prettyPrintString(cumulativeSizes())
		);

	return tr;
	}

ImmutableTreeVector<pair<Fora::PageId, IntegerSequence> > BigVectorPageLayout::slicesCoveringRange(IntegerSequence sequence) const
	{
	if (!sequence.size() || !cumulativeSizes().size())
		return emptyTreeVec();

	sequence = sequence.intersect(IntegerSequence(size()));

	int64_t highValue = sequence.largestValue();
	int64_t lowValue = sequence.smallestValue();

	int64_t sliceContainingLowValue = sliceContaining(cumulativeSizes(), lowValue);
	int64_t sliceContainingHighValue = sliceContaining(cumulativeSizes(), highValue);

	ImmutableTreeVector<pair<Fora::PageId, IntegerSequence> > tr;

	for (long slice = sliceContainingLowValue;
				slice <= sliceContainingHighValue && slice < vectorIdentities().size(); slice++)
		{
		tr = addIfNonempty(
			tr,
			make_pair(
				vectorIdentities()[slice].vector().getPage(),
				IntegerSequence(vectorIdentities()[slice].slice()).slice(
					sequence.offset(-startIndex(slice))
					)
				)
			);
		}

	uint64_t totalCt = 0;
	for (long k = 0; k < tr.size(); k++)
		totalCt += tr[k].second.size();

	lassert_dump(
		totalCt == sequence.size(),
		totalCt << " != " << sequence.size() << ": "
			<< prettyPrintString(vectorIdentities())
			<< " -> "
			<< prettyPrintString(tr)
			<< " and "
			<< prettyPrintString(sequence)
			<< " over range " << sliceContainingLowValue << " to " << sliceContainingHighValue
			<< " which contain values " << lowValue << " and " << highValue
			<< ". cum sizes are " << prettyPrintString(cumulativeSizes())
		);

	return tr;
	}

ImmutableTreeVector<VectorDataIDSlice>
								BigVectorPageLayout::slicesCoveringRange(
											int64_t lowValue,
											int64_t highValue
											) const
	{
	return slicesCoveringRange(IntegerRange(lowValue, highValue));
	}

int64_t BigVectorPageLayout::sliceSize(long slice) const
	{
	return startIndex(slice + 1) - startIndex(slice);
	}

int64_t BigVectorPageLayout::startIndex(long slice) const
	{
	if (slice == 0)
		return 0;

	return cumulativeSizes()[slice - 1];
	}

ImmutableTreeVector<Fora::PageId> BigVectorPageLayout::getPagesReferenced(long indexLow, long indexHigh) const
	{
	ImmutableTreeVector<Fora::PageId> pages;

	while (indexLow < indexHigh)
		{
		long slice = sliceAtIndex(indexLow);

		pages = pages + vectorIdentities()[slice].vector().getPage();

		indexLow = startIndex(slice+1);
		}

	return pages;
	}

ImmutableTreeVector<Fora::PageId> BigVectorPageLayout::getPagesReferenced() const
	{
	ImmutableTreeVector<Fora::PageId> tr;

	for (long k = 0; k < vectorIdentities().size(); k++)
		tr = tr + vectorIdentities()[k].vector().getPage();

	return tr;
	}

uint64_t BigVectorPageLayout::bytecount() const
	{
	if (cumulativeBytecounts().size() == 0)
		return 0;

	return cumulativeBytecounts().back();
	}

pair<int32_t, int32_t> BigVectorPageLayout::fragmentContaining(
													int32_t pageIndex,
													uint32_t fragmentSize
													)
	{
	if (pageIndex == vectorIdentities().size())
		return make_pair(pageIndex, pageIndex);

	lassert(pageIndex >= 0 && pageIndex < vectorIdentities().size());

	uint64_t bytecountAtEnd = cumulativeBytecounts()[pageIndex];
	uint64_t bytecountAtBeginning =
		bytecountAtEnd - vectorIdentities()[pageIndex].vector().getPage().bytecount();

	long fragment = bytecountAtBeginning / fragmentSize;

	uint64_t fragmentOffsetStart = fragment * fragmentSize;

	uint64_t fragmentOffsetStop = fragmentOffsetStart + fragmentSize;

	int32_t pageStart = pageIndex;
	int32_t pageStop = pageIndex;

	while (pageStart > 0 && cumulativeBytecounts()[pageStart - 1] >= fragmentOffsetStart)
		pageStart--;

	while (pageStop + 1 < cumulativeBytecounts().size() &&
					cumulativeBytecounts()[pageStop] < fragmentOffsetStop)
		pageStop++;

	return make_pair(pageStart, pageStop + 1);
	}


BigVectorPageLayout BigVectorPageLayout::concatenate(
											const BigVectorPageLayout& lhs,
											const BigVectorPageLayout& rhs,
											hash_type inGuid
											)
	{
	BigVectorPageLayout result;

	ImmutableTreeVector<VectorDataIDSlice> slices = lhs.vectorIdentities();

	for (long k = 0; k < rhs.vectorIdentities().size(); k++)
		if (slices.size() && slices.back().isSequentialWith(rhs.vectorIdentities()[k]))
			{
			slices = slices.slice(0, slices.size()-1) +
				*slices.back().isSequentialWith(rhs.vectorIdentities()[k]);
			}
		else
			slices = slices + rhs.vectorIdentities()[k];

	JudgmentOnResult jor =
		JudgmentOnValueVector::vectorJOR(
			lhs.jor() + rhs.jor()
			);

	return BigVectorPageLayout(slices, jor, inGuid);
	}

BigVectorPageLayout BigVectorPageLayout::slice(
					int64_t low,
					int64_t high,
					hash_type inGuid
					)
	{
	return slice(null() << low, null() << high, inGuid);
	}

BigVectorPageLayout BigVectorPageLayout::slice(
					Nullable<int64_t> low,
					Nullable<int64_t> high,
					hash_type inGuid
					)
	{
	IntegerRange newRange = IntegerRange(0, size()).slice(low,high);

	return slice(newRange, inGuid);
	}

BigVectorPageLayout BigVectorPageLayout::slice(IntegerRange newRange, hash_type inGuid)
	{
	int64_t lowVal = newRange.low();
	int64_t highVal = newRange.high();

	return BigVectorPageLayout(slicesCoveringRange(lowVal, highVal), jor(), inGuid);
	}


void BigVectorPageLayout::validateInternalState() const
	{
	lassert(vectorIdentities().size() == cumulativeSizes().size());

	int64_t cumulativeOffset = 0;

	for (long k = 0; k < cumulativeSizes().size(); k++)
		{
		cumulativeOffset += vectorIdentities()[k].size();
		lassert(cumulativeSizes().contains(cumulativeOffset));
		}

	lassert(size() == cumulativeOffset);
	}

JudgmentOnResult BigVectorPageLayout::jor() const
	{
	return identity().jor();
	}

Nullable<pair<int64_t, int64_t> > BigVectorPageLayout::mapIndicesToExactSliceRange(
																	Fora::BigVectorSlice slice
																	) const
	{
	int64_t lowSlice = sliceAtIndex(slice.indexLow());
	int64_t highSlice = sliceAtIndex(slice.indexHigh());

	if (startIndex(lowSlice) == slice.indexLow() &&
				startIndex(highSlice) == slice.indexHigh())
		return null() << make_pair(lowSlice, highSlice);

	return null();
	}


}
}
