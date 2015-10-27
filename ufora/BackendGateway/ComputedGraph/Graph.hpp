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

#include "Typedefs.hpp"
#include <stack>
#include <set>
#include "InstanceStorage.hpp"
#include "PropertyStorage.hpp"
#include "../../core/Timers.hpp"
#include "../../core/math/Nullable.hpp"

namespace ComputedGraph {


class Graph : public PolymorphicSharedPtrBase<Graph> {
public:
		Graph();

		~Graph();

		boost::python::object getNode_(boost::python::object inNodeType, boost::python::dict inInstanceData);

		void setnodeProperty(id_type inID, boost::python::object inProp, boost::python::object inVal);

		void flushAll(void);

		void flushLazy(double inTimeout);

		void flush(bool inRecomputeLazy, double inTimeout);

		void flushOrphans();

		boost::python::object nodeAttribute(LocationProperty prop);

		void computeProperty(LocationProperty inNode);

		void registerPropertyName(boost::python::object o);

		boost::python::object idToStringObject(id_type i) const;

		PolymorphicSharedPtr<LocationType> 	getLocationType(const boost::python::object& inNodeType);


		InstanceStorage& getInstanceStorage(void)
			{
			return mInstanceData;
			}

		PropertyStorage& getPropertyStorage(void)
			{
			return mProperties;
			}

		void pushRoot(RootPtr inRoot);

		void popRoot(void);

		RootPtr getCurRoot(void);

private:		
		std::map<id_type, boost::python::object> mKeepAlive;

		std::map<class_id_type, PolymorphicSharedPtr<LocationType> > mNodeTypeMap;	//id of Location class -> class

		std::stack< std::set< LocationProperty > > mComputeStack;

		std::set< LocationProperty > mInCompute_;

		std::vector<LocationProperty> mInComputeOrdered_;

		InstanceStorage mInstanceData;

		PropertyStorage mProperties;

		boost::python::object mCaller;

		boost::python::object mException;

		boost::python::object mExecuteWithinTryBlock;

		boost::python::object mRaiseException, mGetCurTraceback;

		boost::python::object mCycleMaker;

		Nullable<LocationProperty> mCurrentlyComputing;

		std::stack< RootPtr > mRoots;

};

}
