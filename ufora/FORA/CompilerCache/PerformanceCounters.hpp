/***************************************************************************
   Copyright 2015-2016 Ufora Inc.

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
//
class PerformanceCounters {
public:
	PerformanceCounters() :
			mMemoryLookupOps(0),
			mMemoryStoreOps(0),
			mDiskLookupOps(0),
			mDiskStoreOps(0),
			mDiskLookupTime(0),
			mDiskStoreTime(0),
			mSerializationTime(0),
			mDeserializationTime(0)
	{}
	std::string printStats()
		{
		stringstream buffer;
		buffer
			<< "Time spent reading: " << diskLookupTime() << endl
			<< "Time spent writing: " << diskStoreTime() << endl
			<< "Time spent serializing: " << serializationTime() << endl
			<< "Time spent deserializing " << deserializationTime() << endl
			<< "TOTAL DISK TIME:    " << totalTime() << endl
			<< "-----------------------------------" << endl
			<< "Disk Transactions:  " << diskTransactionCount() << endl
			<< "Memory Transactions:" << memoryTransactionCount() << endl
			;
		return buffer.str();
		}

	double totalTime() { return diskLookupTime() + diskStoreTime(); }
	double diskLookupTime() { return mDiskLookupTime; }
	double diskStoreTime() { return mDiskStoreTime; }
	double serializationTime() { return mSerializationTime; }
	double deserializationTime() { return mDeserializationTime; }
	double addDiskLookupTime(double t)
		{
		return mDiskLookupTime += t;
		}
	double addDiskStoreTime(double t)
		{
		return mDiskStoreTime += t;
		}
	double addSerializationTime(double t)
		{
		return mSerializationTime += t;
		}
	double addDeserializationTime(double t)
		{
		return mDeserializationTime += t;
		}
	uint64_t totalTransactionCount()
		{
		return memoryTransactionCount() + diskTransactionCount();
		}
	uint64_t memoryTransactionCount()
		{
		return mMemoryLookupOps + mMemoryStoreOps;
		}
	uint64_t diskTransactionCount()
		{
		return mDiskLookupOps + mDiskStoreOps;
		}
	uint64_t memLookupCount() { return mMemoryLookupOps; }
	uint64_t memStoreCount() { return mMemoryStoreOps; }
	uint64_t diskLookupCount() { return mDiskLookupOps; }
	uint64_t diskStoreCount() { return mDiskStoreOps; }

	uint64_t incrMemLookups() { return ++mMemoryLookupOps; }
	uint64_t incrMemStores() { return ++mMemoryStoreOps; }
	uint64_t incrDiskLookups() { return ++mDiskLookupOps; }
	uint64_t incrDiskStores() { return ++mDiskStoreOps; }

private:
	uint64_t mMemoryLookupOps;
	uint64_t mMemoryStoreOps;
	uint64_t mDiskLookupOps;
	uint64_t mDiskStoreOps;
	double mDiskLookupTime;
	double mDiskStoreTime;
	double mSerializationTime;
	double mDeserializationTime;
};
