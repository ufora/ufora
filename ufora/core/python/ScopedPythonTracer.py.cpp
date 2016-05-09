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
#include <stdint.h>
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "ScopedPythonTracer.hpp"

class ScopedPythonTracerWrapper :
	public native::module::Exporter<ScopedPythonTracerWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "ScopedPythonTracer";
		}

	class ScopedPyTracerWrapper {
	public:
		ScopedPyTracerWrapper(boost::python::object o) : mFunction(o)
			{
			mTracer = 0;
			}

		~ScopedPyTracerWrapper()
			{
			if (mTracer)
				{
				delete mTracer;
				mTracer = 0;
				}
			}
		void enter(void)
			{
			lassert(!mTracer);

			mTracer = new ScopedPythonTracer(mFunction);
			}

		void exit(boost::python::object o1, boost::python::object o2, boost::python::object o3)
			{
			if (mTracer)
				{
				delete mTracer;
				mTracer = 0;
				}
			}

	private:
		ScopedPythonTracer* mTracer;
		boost::python::object mFunction;
	};

	void exportPythonWrapper()
		{
		using namespace boost::python;

		def("extractTimings", &ScopedPythonTracer::extractTimings);
		class_<ScopedPyTracerWrapper>("Tracer", init<boost::python::object>())
			.def("__enter__", &ScopedPyTracerWrapper::enter)
			.def("__exit__", &ScopedPyTracerWrapper::exit)
			;
		}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ScopedPythonTracerWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<ScopedPythonTracerWrapper>::registerWrapper();

