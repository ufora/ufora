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

#include <boost/python.hpp>
#include <map>
#include "../math/StatisticsAccumulator.hpp"

/*******
ScopedPythonTracer

Keeps track of entry/exit from specific python objects.

Clients create a ScopedPythonTracer on the stack with the python object they're about to call.
The system allocates time spent in the objects, tracking them in a list.
*******/

class ComparePythonObjectsByID {
public:
	bool operator()(const boost::python::object& o1, const boost::python::object& o2) const
		{
		return o1.ptr() < o2.ptr();
		}
};

class ScopedPythonTracer {
public:
	ScopedPythonTracer(boost::python::object inObject);

	~ScopedPythonTracer();

	static boost::python::object extractTimings(void);

private:
	static boost::recursive_mutex sMutex;

	static std::map<
				boost::python::object,
				StatisticsAccumulator<double, double>,
				ComparePythonObjectsByID
				> sObjectEntrytimes;

	double mCreationTime;

	double mTimeSpentByChildren;

	boost::python::object mCalledPythonObject;

	ScopedPythonTracer* mEnclosingScope;

	static ScopedPythonTracer* sCurrentTracer;
};


