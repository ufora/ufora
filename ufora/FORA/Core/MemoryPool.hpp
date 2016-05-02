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

#include "../../core/Common.hppml"

namespace Ufora{
namespace threading{

class Trigger;

}
}

namespace Fora {

class ShareableMemoryBlockHandle;
class Pagelet;
class BigVectorId;

}

class VectorPage;
class CallbackScheduler;

/**************

MemoryPool

A generic interface for allocating/deallocating memory.

***************/

class MemoryPool {
public:
	//fast categorization of memory pools for the VectorDataMemoryManager, which needs to track
	//allocations and doesn't have time for RTTI
	enum class MemoryPoolType {
		ExecutionContext,
		VectorPage,
		Pagelet,
		BigVectorHandle,
		DataTask,
		ExternalProcess,
		FreeStore
	};


	MemoryPool(MemoryPoolType inType) :
			mType(inType)
		{
		}

	MemoryPoolType getPoolType() const
		{
		return mType;
		}

	bool isPagelet() const
		{
		return mType == MemoryPoolType::Pagelet;
		}

	bool isBigVectorHandle() const
		{
		return mType == MemoryPoolType::BigVectorHandle;
		}

	bool isDataTasks() const
		{
		return mType == MemoryPoolType::DataTask;
		}

	bool isExecutionContextPool() const
		{
		return mType == MemoryPoolType::ExecutionContext;
		}

	bool isVectorPage() const
		{
		return mType == MemoryPoolType::VectorPage;
		}

	virtual std::string stringRepresentation() = 0;

	static MemoryPool* getFreeStorePool();

	virtual ~MemoryPool() {};

	virtual Fora::ShareableMemoryBlockHandle convertPointerToShareableMemoryBlock(uint8_t* inBytes, int64_t bytes) = 0;

	virtual uint8_t* importShareableMemoryBlock(const Fora::ShareableMemoryBlockHandle& inHandle) = 0;

	virtual void incrementBigVectorRefcount(const Fora::BigVectorId& identity) {};

	virtual void decrementBigVectorRefcount(const Fora::BigVectorId& identity) {};

	virtual size_t totalBytesAllocated() const = 0;

	virtual size_t totalBytesAllocatedFromOS() const = 0;

	virtual size_t totalBytesFromOSHeldInPagelets() const = 0;

	virtual size_t totalBytesAllocatedFromOSExcludingPagelets() const = 0;

	virtual uint8_t* allocate(size_t inBytes) = 0;

	virtual void free(uint8_t* inBytes) = 0;

	virtual uint8_t* realloc(uint8_t* inBytes, uword_t inNewBytes) = 0;

	virtual bool permitAllocation(size_t inBytes) = 0;

	virtual void vectorPageMapped(
						boost::shared_ptr<VectorPage> mappedPage,
						boost::shared_ptr<Ufora::threading::Trigger> mappedPageWantsUnmapped
						) = 0;

	virtual bool isVectorPageMapped(
						boost::shared_ptr<VectorPage> mappedPage
						) = 0;

	virtual void pageletIsHeld(boost::shared_ptr<Fora::Pagelet> inPagelet) {};

	virtual void pageletIsNoLongerHeld(boost::shared_ptr<Fora::Pagelet> inPagelet) {};

	template<class T>
	void destroy(T* inT)
		{
		inT->~T();

		free((uint8_t*)inT);
		}

	template<class T>
	T* construct()
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T();

		return result;
		}

	template<class T, class A1>
	T* construct(const A1& a1)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1);

		return result;
		}

	template<class T, class A1, class A2>
	T* construct(const A1& a1, const A2 &a2)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2);

		return result;
		}

	template<class T, class A1, class A2, class A3>
	T* construct(const A1& a1, const A2 &a2, const A3& a3)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4, class A5>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4, const A5& a5)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4,a5);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4, class A5, class A6>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4, const A5& a5, const A6& a6)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4,a5,a6);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4, const A5& a5, const A6& a6, const A7& a7)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4,a5,a6,a7);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, class A8>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4, const A5& a5, const A6& a6, const A7& a7, const A8& a8)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4,a5,a6,a7,a8);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, class A8, class A9>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4, const A5& a5, const A6& a6, const A7& a7, const A8& a8, const A9& a9)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4,a5,a6,a7,a8,a9);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, class A8, class A9, class A10>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4, const A5& a5, const A6& a6, const A7& a7, const A8& a8, const A9& a9, const A10& a10)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4,a5,a6,a7,a8,a9,a10);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, class A8, class A9, class A10, class A11>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4, const A5& a5, const A6& a6, const A7& a7, const A8& a8, const A9& a9, const A10& a10, const A11& a11)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11);

		return result;
		}

	template<class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, class A8, class A9, class A10, class A11, class A12>
	T* construct(const A1& a1, const A2 &a2, const A3& a3, const A4& a4, const A5& a5, const A6& a6, const A7& a7, const A8& a8, const A9& a9, const A10& a10, const A11& a11, const A12& a12)
		{
		T* result = (T*)allocate(sizeof(T));
		if (!result)
			return 0;

		new (result) T(a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12);

		return result;
		}

private:
	MemoryPoolType mType;
};

std::ostream& operator<<(std::ostream& s, MemoryPool* pool);




