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
#include "ScopedPythonTracer.hpp"
#include "../Clock.hpp"

ScopedPythonTracer::ScopedPythonTracer(boost::python::object inObject)
	{
	mCalledPythonObject = inObject;
	mCreationTime = curClock();
	mEnclosingScope = sCurrentTracer;
	sCurrentTracer = this;
	mTimeSpentByChildren = 0;
	}

ScopedPythonTracer::~ScopedPythonTracer()
	{
	boost::recursive_mutex::scoped_lock lock(sMutex);

	double finTime = curClock();

	double totalTimeWithin = finTime - mCreationTime;

	sObjectEntrytimes[mCalledPythonObject].observe(totalTimeWithin - mTimeSpentByChildren, 1.0);

	if (mEnclosingScope)
		mEnclosingScope->mTimeSpentByChildren += totalTimeWithin;

	sCurrentTracer = mEnclosingScope;
	}

boost::python::object ScopedPythonTracer::extractTimings(void)
	{
	boost::recursive_mutex::scoped_lock lock(sMutex);

	boost::python::dict d;

	for (auto it = sObjectEntrytimes.begin(), it_end = sObjectEntrytimes.end(); it != it_end; ++it)
		d[it->first] = boost::python::make_tuple(it->second.mean(), it->second.weight());

	sObjectEntrytimes.clear();

	return d;
	}

boost::recursive_mutex ScopedPythonTracer::sMutex;

std::map<
	boost::python::object,
	StatisticsAccumulator<double, double>,
	ComparePythonObjectsByID
	> ScopedPythonTracer::sObjectEntrytimes;

ScopedPythonTracer* ScopedPythonTracer::sCurrentTracer;



