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
#include "FunctionPointerTable.hpp"

#include <stdexcept>
#include <sstream>

#include "../../core/Logging.hpp"

using namespace std;
using namespace boost;

typedef FunctionPointerTable::slot_identifier_type slot_identifier_type;

bool FunctionPointerTable::hasSlot(const slot_identifier_type& name) const
	{
    boost::recursive_mutex::scoped_lock lock(mMutex);

	return mSlots.count(name) != 0;
	}

bool FunctionPointerTable::hasNonNull(const slot_identifier_type& name) const
	{
    boost::recursive_mutex::scoped_lock lock(mMutex);

	return mSlots.count(name) && !mSlots.at(name).isEmpty();
	}

//This should probably return a const function pointer slot
FunctionPointerHandle
FunctionPointerTable::getExistingSlot(const slot_identifier_type& name) const
	{
    boost::recursive_mutex::scoped_lock lock(mMutex);

	if (mSlots.count(name) == 0)
		throw logic_error("No function pointer slot for " + name.first +
		                  " found in table.");
	return mSlots.at(name);
	}

void FunctionPointerTable::createNullSlots(const std::vector<slot_identifier_type>& names)
	{
    boost::recursive_mutex::scoped_lock lock(mMutex);
	
	for (long k = 0; k < names.size();k++)
		if (mSlots.count(names[k]) != 0)
			throw logic_error("Already have function pointer slot for " +
							  names[k].first + ".");
	
	FunctionPointerArray*	array = new FunctionPointerArray(names.size());

	for (long k = 0; k < names.size();k++)
		mSlots.insert(make_pair(names[k], array->getHandle(k)));

	mSlotCreated.notify_all();
	}

void FunctionPointerTable::updateSlotContents(
									const slot_identifier_type& name,
									long versionNumber,
                                    NativeFunctionPointerAndEntrypointId newContents
                                    )
	{
	if (newContents.isEmpty())
		throwLogicErrorWithStacktrace(
			"Cannot place a null pointer in the slot contents.");
	
    boost::recursive_mutex::scoped_lock lock(mMutex);

    if (mSlotVersionNumbers.find(name) != mSlotVersionNumbers.end() &&
    		mSlotVersionNumbers[name] > versionNumber)
    	return;

    mSlotVersionNumbers[name] = versionNumber;
	
	if (mSlots.count(name) == 0)
		throwLogicErrorWithStacktrace(
			"FuncPtrSlot not yet created for " + name.first + ".");
	
	//verify that the slot has been initialized
	FunctionPointerHandle slot = mSlots.find(name)->second;
	
	if (slot.isEmpty())
		throwLogicErrorWithStacktrace(
			"FuncPtrSlot not yet initialized for " + name.first
					+ " but we're trying to initialize it."
					);
	
	slot.update(newContents);
	}

void FunctionPointerTable::initializeSlotContents(
		const std::map<slot_identifier_type, NativeFunctionPointerAndEntrypointId>& inDefinitions
		)
	{
    boost::recursive_mutex::scoped_lock lock(mMutex);

	map<FunctionPointerArray*, std::vector<NativeFunctionPointerAndEntrypointId> > pointers;
	
	for (std::map<slot_identifier_type, NativeFunctionPointerAndEntrypointId>::const_iterator it =
				inDefinitions.begin(), it_end = inDefinitions.end();
			it != it_end;
			++it)
		{
		if (!hasSlot(it->first))
			throwLogicErrorWithStacktrace("can't initialize a slot we have "
				"not defined.");

		FunctionPointerHandle handle = getExistingSlot(it->first);
		
		FunctionPointerArray* array = handle.getArray();
		
		if (!array->isEmpty())
			throwLogicErrorWithStacktrace("array at " + it->first.first + " is already"
				" initialized.");
		
		//make sure all the slots are filled out
		if (pointers.find(array) == pointers.end())
			pointers[array].resize(array->size());
		
		pointers[array][handle.getIndex()] = it->second;
		}
	
	for (std::map<FunctionPointerArray*,
			std::vector<NativeFunctionPointerAndEntrypointId> >::const_iterator
				it = pointers.begin(),
				it_end = pointers.end();
			it != it_end;
			++it)
		{
		for (long k = 0; k < it->second.size();k++)
			if (it->second[k].isEmpty())
				throwLogicErrorWithStacktrace("didn't initialize an "
					"array slot.");
		
		//initialize this array with these pointers
		it->first->fillArray(it->second);
		}
	}

void FunctionPointerTable::blockUntilSlotExists(const slot_identifier_type& name) const
	{
    boost::recursive_mutex::scoped_lock lock(mMutex);

    while (!hasSlot(name))
    	mSlotCreated.wait(lock);
	}

