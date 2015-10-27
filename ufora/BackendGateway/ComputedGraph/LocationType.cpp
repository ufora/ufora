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
#include "Graph.hpp"
#include "LocationType.hpp"
#include "../../core/python/utilities.hpp"

using namespace Ufora::python;

namespace ComputedGraph {

LocationType::LocationType(Graph* inGraph, boost::python::object inClass)
	{
	update(inGraph, inClass);
	}

void LocationType::update(Graph* inGraph, boost::python::object inClass)
	{
	mClass = inClass;

	mFunctions.clear();
	mProperties.clear();
	mMutables.clear();
	mKeys.clear();
	mKeyDefaults.clear();
	mKeyValidators.clear();
	mAttrTypes.clear();

	mDefersTo = boost::python::object();

	boost::python::object pyIsMutable = evalInModule("lambda x: isinstance(x, Mutable)", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	boost::python::object pyIsKey = evalInModule("lambda x: isinstance(x, Key)", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	boost::python::object pyIsType = evalInModule("lambda x: isinstance(x, type(Key))", "ufora.BackendGateway.ComputedGraph.ComputedGraph");

	boost::python::object pySimpleSeq = evalInModule("lambda x: isSimpleFunction(x)[1]", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	boost::python::object pyIsFunction = evalInModule("lambda x: isinstance(x, Function)", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	boost::python::object pyIsProperty = evalInModule("lambda x: isinstance(x, Property)", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	boost::python::object pyIsInitializer = evalInModule("lambda x: isinstance(x, Initializer)", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	boost::python::object pyIsPythonFunction = evalInModule("lambda x: isinstance(x, functype)", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	boost::python::object pyIsNotCached = evalInModule("lambda x: isinstance(x, NotCached)", "ufora.BackendGateway.ComputedGraph.ComputedGraph");

	boost::python::dict members(evalInModule("getClassMember", "ufora.BackendGateway.ComputedGraph.ComputedGraph")(inClass));
	py_list instItems = members.items();
	for (int32_t i = 0; i < len(instItems); i++)
		{
		boost::python::object attrName = instItems[i][0];
		string attrNameStr = pyToString(attrName);

		boost::python::object attrVal = instItems[i][1];
		id_type attrID = id(attrName);

		inGraph->registerPropertyName(attrName);

		if (pyIsInitializer(attrVal))
			mInitializer = attrVal.attr("f");
			else
		if (pyIsMutable(attrVal))
			{
			boost::python::object onChanged = attrVal.attr("onUpdate");
			boost::python::object defaultValue = attrVal.attr("defaultValue");

			mMutables[attrID] = make_pair(defaultValue, onChanged);

			mAttrTypes[attrID] = attrMutable;
			}
			else
		if (pyIsKey(attrVal))
			{
			mKeys[attrID] = attrVal.attr("t");
			mAttrTypes[attrID] = attrKey;
			mKeyDefaults[attrID] = attrVal.attr("default");
			mKeyValidators[attrID] = attrVal.attr("validator");
			}
			else
		if (pyIsFunction(attrVal))
			{
			mAttrTypes[attrID] = attrFunction;
			mFunctions[attrID] = attrVal.attr("f");
			}
			else
		if (pyIsNotCached(attrVal))
			{
			mAttrTypes[attrID] = attrNotCached;
			mFunctions[attrID] = attrVal.attr("f");
			}
			else
		if (pyIsType(attrVal)) //a key by default
			{
			mKeys[attrID] = attrVal;
			mKeyDefaults[attrID] = boost::python::object();
			mAttrTypes[attrID] = attrKey;
			mKeyValidators[attrKey] = boost::python::object();
			}
			else
		if (pyIsPythonFunction(attrVal))
			{
			mProperties[attrID] = attrVal;
			mAttrTypes[attrID] = attrProperty;
			}
			else
		if (pyIsProperty(attrVal))
			{
			mProperties[attrID] = attrVal.attr("cacheFunc");
			
			boost::python::object setter = attrVal.attr("setter");
			
			//if the setter is 'None', there's no setter
			if (setter.ptr() != boost::python::object().ptr())
				mPropertySetters[attrID] = setter;

			//is the property lazy?
			mIsLazyProperty[attrID] = boost::python::extract<bool>(attrVal.attr("isLazy"))();
			
			mAttrTypes[attrID] = attrProperty;
			}
			else
		if (attrNameStr.size() && attrNameStr[attrNameStr.size()-1] != '_')
			{
			mClassAttributes[attrID] = attrVal;
			mAttrTypes[attrID] = attrClassAttribute;
			}
		}
	}
string LocationType::name(void) const
	{
	return pyToString(mClass);
	}

attr_type LocationType::getAttrType(const id_type& inID) const
	{
	map<id_type, attr_type>::const_iterator it = mAttrTypes.find(inID);
	if (it == mAttrTypes.end())
		return attrUnknown;
	return it->second;
	}
boost::python::object LocationType::getClass(void) const
	{
	return mClass;
	}
class_id_type LocationType::getClassID(void) const
	{
	return make_pair(id(mClass.attr("__module__")), id(mClass.attr("__name__")));
	}
bool	LocationType::isLazy(const id_type& inID) const
	{
	map<id_type, bool>::const_iterator it = mIsLazyProperty.find(inID);
	if (it != mIsLazyProperty.end())
		return it->second;
	return false;
	}

}






