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
#include <boost/python.hpp>
#include "Logging.hpp"
#include "../native/Registrar.hpp"
#include "python/CPPMLWrapper.hpp"
#include "python/ScopedPyThreads.hpp"
#include "Platform.hpp"
#include "Memory.hpp"
#include "Clock.hpp"

#include <gperftools/malloc_extension.h>
#include <gperftools/heap-profiler.h>

#ifdef HAVE_PROFILER
#include <gperftools/profiler.h>
#endif

namespace Ufora {

class TCMallocWrapper :
		public native::module::Exporter<TCMallocWrapper> {
public:
		std::string getModuleName(void)
			{
			return "TCMalloc";
			}

		static bool tcMallocIsEnabled()
			{
			return true;
			}

		static boost::python::object getMemoryStat(std::string inName)
			{
			size_t out;

			if (MallocExtension::instance()->GetNumericProperty(inName.c_str(), &out))
				return boost::python::object(out);

			return boost::python::object();
			}

		static boost::python::object getBytesUsed()
			{
			return getMemoryStat("generic.current_allocated_bytes");
			}
		static boost::python::object totalBytesAllocatedFromOS()
			{
			return getMemoryStat("generic.heap_size");
			}
		static void heapProfilerStart(std::string s)
			{
			LOG_INFO << "starting heap profiler. dumping to " << s << "\n";
			HeapProfilerStart(s.c_str());
			}
		static void heapProfileDump(std::string s)
			{
			LOG_INFO << "dumping a heap. reason: " << s << "\n";
			}
		static bool isHeapProfilerRunning(void)
			{
			return IsHeapProfilerRunning();
			}
		static void heapProfilerStop(void)
			{
			HeapProfilerStop();
			}

		static void cpuProfilerStart(std::string name)
			{
			#ifdef HAVE_PROFILER
			ProfilerStart(name.c_str());
			#endif
			}

		static void cpuProfilerStop()
			{
			#ifdef HAVE_PROFILER
			ProfilerStop();
			#endif
			}

		static uword_t mallocAndReturnAddress(uword_t count)
			{
			return (uword_t) Ufora::Memory::bsa_malloc(count);
			}

		static uword_t reallocAtAddress(uword_t inData, uword_t count)
			{
			return (uword_t) Ufora::Memory::bsa_realloc((void*)inData, count);
			}

		static void freeAtAddress(uword_t address)
			{
			return Ufora::Memory::bsa_free((void*)address);
			}

		static std::string returnStringArg(const std::string& inString)
			{
			return inString;
			}

		static std::string getCPPMLSummary(double megabyteThreshold)
			{
			std::ostringstream str;

			#ifdef CPPML_TRACK_INSTANCE_COUNTS

			std::map<std::string, unsigned long> counts =
				CPPML::AllInstanceCounts::singleton().getCounts();

			std::map<std::string, unsigned long> byteCounts =
				CPPML::AllInstanceCounts::singleton().getByteCounts();

			for (auto it = counts.begin(); it != counts.end(); ++it)
				if (byteCounts[it->first] > megabyteThreshold * 1024 * 1024)
					str << it->second << "\t" << byteCounts[it->first]/1024/1024.0 << " MB\t" << it->first << "\n";

			#endif

			return str.str();
			}

		static double getMemBenchmark(double benchmarkTime)
			{
			double t0 = curClock();
			long ct = 0;

			while (curClock() - t0 < benchmarkTime)
				{
				for (long k = 0; k < 1000;k++)
					free(malloc(128));
				ct += 1000;
				}

			return ct / (curClock() - t0);
			}

		static double getLoopBenchmark(double benchmarkTime)
			{
			double t0 = curClock();
			long ct = 0;
			double f = curClock();
			while (curClock() - t0 < benchmarkTime)
				{
				for (long k = 0; k < 100000;k++)
					f = (f + 1.0) / 2.0;

				ct += 1;
				}

			LOG_DEBUG << "result: " << f;

			return ct / (curClock() - t0) * 100000;
			}

		static double getClockBenchmark(double benchmarkTime)
			{
			double t0 = curClock();
			long ct = 0;
			float f = 1.0;
			while (curClock() - t0 < benchmarkTime)
				ct += 1;

			return ct / (curClock() - t0);
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			def("getMemBenchmark", &getMemBenchmark);
			def("getLoopBenchmark", &getLoopBenchmark);
			def("getClockBenchmark", &getClockBenchmark);
			def("getMemoryStat", &getMemoryStat);
			def("getBytesUsed", &getBytesUsed);
			def("totalBytesAllocatedFromOS", &totalBytesAllocatedFromOS);
			def("startHeapProfiling", &heapProfilerStart);
			def("dumpHeapProfile", &heapProfileDump);
			def("cpuProfilerStart", &cpuProfilerStart);
			def("cpuProfilerStop", &cpuProfilerStop);
			def("mallocAndReturnAddress", mallocAndReturnAddress);
			def("reallocAtAddress", reallocAtAddress);
			def("freeAtAddress", freeAtAddress);
			def("returnStringArg", returnStringArg);

			def("isHeapProfilerRunning", &isHeapProfilerRunning);
			def("stopHeapProfiling", &heapProfilerStop);

			def("getCPPMLSummary", &getCPPMLSummary);

			def("isEnabled", tcMallocIsEnabled);
			}
};

}

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<
	Ufora::TCMallocWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			Ufora::TCMallocWrapper>::registerWrapper();

