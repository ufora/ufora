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
#include "Graph.hpp"

namespace ComputedGraph {

class Root : public PolymorphicSharedPtrBase<Root> {
public:
		Root(PolymorphicSharedPtr<Graph> inGraph) : mGraph(inGraph)
			{
			}
		PolymorphicSharedPtr<Root> polymorphicSharedPtrFromThis() const
			{
			return PolymorphicSharedPtr<Root>(this->polymorphicSharedPtrFromThis());
			}

		virtual ~Root()
			{
			}

		virtual void changed()
			{
			}

		virtual void addDependency(const LocationProperty& inProp)
			{
			mRoots.insert(inProp);
			}

		static void enter(PolymorphicSharedPtr<Root>& inRoot)
			{
			inRoot->mGraph->pushRoot(inRoot->polymorphicSharedPtrFromThis());
			}

		static void exit(	PolymorphicSharedPtr<Root>& inRoot,
							boost::python::object o,
							boost::python::object o2,
							boost::python::object o3
							)
			{
			inRoot->mGraph->popRoot();
			}
protected:
		std::set<LocationProperty> mRoots;

		PolymorphicSharedPtr<Graph> mGraph;
};

class ScopedComputedGraphRoot {
public:
		ScopedComputedGraphRoot(PolymorphicSharedPtr<Graph> inGraph) : mGraph(inGraph)
			{
			mGraph->pushRoot(mRoot);
			}
		ScopedComputedGraphRoot(RootPtr inRoot, PolymorphicSharedPtr<Graph> inGraph) : mRoot(inRoot), mGraph(inGraph)
			{
			mGraph->pushRoot(mRoot);
			}
		~ScopedComputedGraphRoot()
			{
			mGraph->popRoot();
			}
private:
		RootPtr mRoot;

		PolymorphicSharedPtr<Graph> mGraph;
};

}

