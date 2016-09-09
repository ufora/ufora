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
#include "Root.hpp"
#include "LocationType.hpp"
#include "../../core/python/utilities.hpp"
#include "../../core/python/ScopedPythonTracer.hpp"

using namespace Ufora::python;

namespace ComputedGraph {

Graph::Graph() : mProperties(this)
	{
	mExecuteWithinTryBlock = evalInModule("executeWithinTryBlock", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	mRaiseException = evalInModule("raiseException", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	mGetCurTraceback = evalInModule("lambda: sys.exc_info()[2]", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	mCaller = evalInModule("Caller_", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	mCycleMaker = evalInModule("DependencyCycle", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	}

Graph::~Graph()
	{
	}

boost::python::object Graph::getNode_(boost::python::object inNodeType, boost::python::dict inInstanceData)
	{
	PolymorphicSharedPtr<LocationType> typePtr = getLocationType(inNodeType);
	bool needsInit;

	Location location =
		mInstanceData.getObject(
			this->polymorphicSharedPtrFromThis(),
			typePtr,
			inInstanceData,
			needsInit
			);

	boost::python::object o = location.getPythonObject().attr("__dict__");

	if (needsInit)
		{
		for (std::map<id_type, boost::python::object>::const_iterator it = typePtr->mKeys.begin(); it != typePtr->mKeys.end(); ++it)
			{
			id_type attrID = it->first;
			boost::python::object attr = idToStringObject(attrID);

			if (typePtr->mKeyValidators[attrID] != boost::python::object())
				{
				bool valid = typePtr->mKeyValidators[attrID](location.getKey(attrID));

				if (! valid )
					{
					string s = "<couldn't compute str of argument>";
					try {
						s = pyToString(location.getKey(attrID));
						}
					catch(...) {}
					throw std::logic_error("setting " + pyToString(attr) + " = " + s + " in " + typePtr->name() + " failed validation");
					}
				}

			o[attr] = location.getKey(attrID);
			}
		for (std::map<id_type, boost::python::object>::const_iterator it = typePtr->mClassAttributes.begin(); it != typePtr->mClassAttributes.end(); ++it)
			o[idToStringObject(it->first)] = it->second;

		for (std::map<id_type, pair<boost::python::object, boost::python::object> >::const_iterator it = typePtr->mMutables.begin(); it != typePtr->mMutables.end(); ++it)
			{
			id_type propID = it->first;
			boost::python::object defaultValue = it->second.first;

			if (defaultValue != boost::python::object())
				{
				boost::python::object defaultResult = defaultValue();

				location.setMutable(propID, defaultResult);
				lassert(location.getMutable(propID) == defaultResult);
				}
			else
				location.setMutable(propID, boost::python::object());
			}

		if (typePtr->mInitializer != boost::python::object())
			typePtr->mInitializer(location.getPythonObject());
		}

	return location.getPythonObject();
	}

void Graph::setnodeProperty(id_type inID, boost::python::object inProp, boost::python::object inVal)
	{
	registerPropertyName(inProp);

	Location l = mInstanceData.getObjectFromID(inID);
	PolymorphicSharedPtr<LocationType> nodeType = l.getType();

	id_type propID = id(inProp);

	if (l.attributeType(propID) == attrProperty)
		{
		lassert_dump(nodeType->mPropertySetters.find(propID) != nodeType->mPropertySetters.end(), "property is not settable!");
		nodeType->mPropertySetters[propID](l.getPythonObject(), inVal);
		return;
		}

	lassert_dump(l.attributeType(propID) == attrMutable, "cannot assign " << pyToString(inVal) << " to " << l.name() << ":" << pyToString(inProp) << " as it is not mutable." );

	if (inVal == l.getMutable(propID))
		return;

	boost::python::object oldValue(l.getMutable(propID));

	l.setMutable(propID, inVal);

	if (nodeType->mMutables[id(inProp)].second != boost::python::object())
		//calling the "onUpdate" function
		nodeType->mMutables[id(inProp)].second( l.getPythonObject(), oldValue, inVal );
	}

void Graph::flushAll(void)
	{
	flush(false, -1.0);
	}

void Graph::flushLazy(double inTimeout)
	{
	flush(true, inTimeout);
	}

//set inTimeout to something negative to have no timeout
void Graph::flush(bool inRecomputeLazy, double inTimeout)
	{
	double t0 = curClock();
	int32_t sinceComputed = 0;
	int32_t reLeveld = 0;
	int32_t reComputed = 0;
	int32_t orphaned = 0;

	std::set<LocationProperty> distinct, pending;
	int32_t leveledSinceCompute = 0;
	bool cleared = false;

	uint32_t lazyUpdateCt = 0;
	uint32_t nonlazyUpdateCt = 0;

	while (mProperties.hasDirty(inRecomputeLazy) && (inTimeout < 0.0 || curClock() - t0 < inTimeout))
		{
		LocationProperty p = mProperties.getLowestDirty(inRecomputeLazy);
		distinct.insert(p);

		(mProperties.isLazy(p) ? lazyUpdateCt : nonlazyUpdateCt)++;

		if (mProperties.recomputeLaziness(p))
			{
			//pass and grab a new node
			}
			else
		if (!mProperties.recomputeLevel(p))
			{
			computeProperty(p);
			reComputed++;
			leveledSinceCompute = 0;
			pending.erase(p);
			}
			else
			{
			if (pending.find(p) == pending.end())
				{
				pending.insert(p);
				leveledSinceCompute = 0;
				}
				else
				{
				leveledSinceCompute++;
				if (leveledSinceCompute > pending.size() * 2 + 2)
					{
					//we must have a cycle.
					if (!cleared)
						{
						cleared = true;
						pending = set<LocationProperty>();
						leveledSinceCompute = 0;
						}
						else
						{
						boost::python::object o = mCycleMaker();
						for (std::set<LocationProperty>::iterator it = pending.begin(); it != pending.end(); ++it)
							{
							o.attr("cycle").attr("append")(boost::python::make_tuple(it->getLocation().getPythonObject(), it->propertyNameObject()));
							mProperties.setProperty(*it, o, set<LocationProperty>());
							}
						}
					leveledSinceCompute = 0;
					pending = set<LocationProperty>();
					}
				}
			}

		reLeveld++;
		}

	if (lazyUpdateCt || nonlazyUpdateCt)
		mProperties.scanRootsAndDrop();
	}

void Graph::flushOrphans(void)
	{
	while (mProperties.getNonrootNonmutableOrphans().size())
		mProperties.deleteOrphan(*mProperties.getNonrootNonmutableOrphans().begin());
	}

boost::python::object Graph::nodeAttribute(LocationProperty prop)
	{
	RootPtr curRoot = getCurRoot();
	if (curRoot)
		{
		curRoot->addDependency(prop);
		mProperties.addRootNode(prop, curRoot);
		}

	attr_type 			attributeType = prop.attributeType();

	if (attributeType == attrClassAttribute)
		return prop.getClassAttribute();

	if (attributeType == attrUnknown)
		return prop.getUnknown();

	if (mComputeStack.size() == 0 && mRoots.size() == 0)
		if (attributeType == attrMutable)
			return prop.getMutable();

	if (attributeType == attrFunction)
		return mCaller(prop.getFunction(), prop.getLocation().getPythonObject());

	if (attributeType == attrNotCached)
		return prop.getFunction()(prop.getLocation().getPythonObject());

	if (attributeType == attrKey)
		return prop.getKey();

	if (mComputeStack.size() == 0 && mRoots.size() == 0)
		flushAll();

	if (mComputeStack.size() != 0)
		mComputeStack.top().insert(prop);

	if (attributeType == attrMutable)
		return prop.getMutable();

	//the first time we've ever seen it
	if (!prop.hasProperty())
		{
		if (prop.isLazy())
			{
			//the first time we see a lazy property,
			//just initialize it to none and mark it dirty
			mProperties.setProperty(prop, boost::python::object(), set< LocationProperty >());
			mProperties.setClean(prop, false);
			}
		else
			{
			if (mInCompute_.find(prop) != mInCompute_.end())
				{
				mComputeStack.top().erase(prop);
				throw std::logic_error("can't compute " + prop.name() + " as it is recursing!");
				}

			computeProperty(prop);
			}
		}

	boost::python::object tr = prop.getProperty();

	if (PyObject_IsInstance(tr.ptr(), PyExc_Exception))
		mRaiseException(tr);

	return tr;
	}



class LocationPropertyRoot : public Root {
public:
		LocationPropertyRoot(PolymorphicSharedPtr<Graph> inGraph, LocationProperty inProperty) :
									Root(inGraph),
									mProperty(inProperty)
			{
			}

		virtual void changed()
			{
			mGraph->getPropertyStorage().setClean(mProperty, false);
			}

private:
		LocationProperty mProperty;
};

void Graph::computeProperty(LocationProperty inNode)
	{
	PolymorphicSharedPtr<Root> rootPtr(
		new LocationPropertyRoot(
			this->polymorphicSharedPtrFromThis(),
			inNode
			)
		);

	ScopedComputedGraphRoot setRoot(
		rootPtr,
		this->polymorphicSharedPtrFromThis()
		);

	mComputeStack.push(std::set<LocationProperty>());
	mInCompute_.insert(inNode);
	mInComputeOrdered_.push_back(inNode);

	boost::python::object val;

	mCurrentlyComputing = inNode;

		{
		val = mExecuteWithinTryBlock(inNode.propertyDefinition(), inNode.getLocation().getPythonObject());
		}

	mCurrentlyComputing = null();

	mProperties.setProperty(inNode, val, mComputeStack.top());

	mComputeStack.pop();
	mInCompute_.erase(inNode);
	mInComputeOrdered_.pop_back();
	}

void Graph::registerPropertyName(boost::python::object o)
	{
	if (mKeepAlive.find(id(o)) == mKeepAlive.end())
		mKeepAlive[id(o)] = o;
	}

boost::python::object Graph::idToStringObject(id_type i) const
	{
	lassert_dump(mKeepAlive.find(i) != mKeepAlive.end(), i << " in " << /*(uint32_t) this*/"ADDR" << " with " << mKeepAlive.size() << " total");
	return mKeepAlive.find(i)->second;
	}

PolymorphicSharedPtr<LocationType> 	Graph::getLocationType(const boost::python::object& inNodeType)
	{
	//register with the reloader
	class_id_type identifier(id(inNodeType.attr("__module__")), id(inNodeType.attr("__name__")));

	if (mNodeTypeMap.find(identifier) == mNodeTypeMap.end())
		{
		mNodeTypeMap[identifier] = PolymorphicSharedPtr<LocationType>(new LocationType(this, inNodeType));
		}

	return mNodeTypeMap[identifier];
	}

void Graph::pushRoot(RootPtr inRoot)
	{
	mRoots.push(inRoot);
	}

void Graph::popRoot(void)
	{
	mRoots.pop();
	}

RootPtr Graph::getCurRoot(void)
	{
	if (!mRoots.size())
		return RootPtr();
	return mRoots.top();
	}

}

