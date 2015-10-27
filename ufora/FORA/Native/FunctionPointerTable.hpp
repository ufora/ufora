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

#include "FunctionPointerHandle.hpp"
#include "NativeCode.hppml"
#include <boost/lexical_cast.hpp>
#include <boost/thread.hpp>
#include <boost/utility.hpp>
#include <map>
#include <string>

//A table for maintaining function pointer slots and the correspondence
//between function pointers and function names.
//the table is fully thread-safe - all operations proceed underneath a
//single object-wide lock.
class FunctionPointerTable : boost::noncopyable {
public:
	typedef std::pair<std::string, NativeBlockID> slot_identifier_type;

	//States whether this table has a function pointer slot
	//for the given function.
	bool hasSlot(const slot_identifier_type& name) const;
	
	//Returns true iff this table has a slot for the specified
	//function and that slot's contents are nonnull.
	bool hasNonNull(const slot_identifier_type& name) const;
	
	//Gets the slot for the specified function.
	//It is illegal to call this function with a name that has
	//not previously been passed to createNullSlot.
	FunctionPointerHandle getExistingSlot(const slot_identifier_type& name) const;
	
	
	//Creates a set of slots for each of the specified function names.
	//The function names must be new, or a logic_error will be thrown.
	//the functions are all tied together in a single FunctionPointerArray
	//and must be initialized all at once
	void createNullSlots(const std::vector<slot_identifier_type>& name);
	
	//initialize a set of slots.  If every FunctionPointerArray that is
	//represented in the names must be fully represented (e.g. we have to
	//be able to initialize the whole set of them) and they cannot ever
	//have been initialized.
	void initializeSlotContents(
			const std::map<slot_identifier_type, NativeFunctionPointerAndEntrypointId>& inDefinitions
			);
	
	//Sets the contents of the slot for the specified function.
	//This table must have a slot for that function, and the
	//intended contents shall not have been used previously
	//under a different function name.
	void updateSlotContents(
					const slot_identifier_type& name,
					long versionNumber,
					NativeFunctionPointerAndEntrypointId newContents
					);
	
	void blockUntilSlotExists(const slot_identifier_type& name) const;

private:
	std::map<slot_identifier_type, FunctionPointerHandle> mSlots;

	std::map<slot_identifier_type, long> mSlotVersionNumbers;

	mutable boost::recursive_mutex mMutex;

	mutable boost::condition_variable_any mSlotCreated;
};

