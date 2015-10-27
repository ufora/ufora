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

#include "../../FORA/Core/Type.hppml"
#include "../../core/PolymorphicSharedPtr.hpp"
#include <boost/python.hpp>
#include <map>
#include <string>

#define COMPUTED_GRAPH_TIMING 1

namespace ComputedGraph {

typedef boost::python::list py_list;

typedef unsigned long id_type;
typedef std::pair<id_type, id_type> class_id_type;

typedef enum { 
	attrKey, 
	attrMutable, 
	attrProperty, 
	attrFunction, 
	attrNotCached, 
	attrClassAttribute, 
	attrUnknown 
} attr_type;

class Graph;

class Location;

class LocationProperty;

class Root;

class LocationType;

class PropertyStorage;

class InstanceStorage;

typedef PolymorphicSharedPtr<Root> RootPtr;
typedef PolymorphicSharedWeakPtr<Root> WeakRootPtr;

}

