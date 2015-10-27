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
#include "../FORA/python/FORAPythonUtil.hppml"
#include "../native/Registrar.hpp"
#include "../core/python/CPPMLWrapper.hpp"
#include "../core/containers/ImmutableTreeVector.py.hpp"
#include "SystemwideComputationScheduler/LocalSchedulerSimulator.hppml"
#include "CumulusWorkerEventSimulator.hppml"
#include "../core/serialization/IFileProtocol.hpp"

using namespace Cumulus;

using SystemwideComputationScheduler::LocalSchedulerSimulator;

class CumulusWorkerEventSimulatorWrapper :
		public native::module::Exporter<CumulusWorkerEventSimulatorWrapper> {
public:
		std::string	     getModuleName(void)
			{
			return "Cumulus";
			}

		static void replayCumulusWorkerEventStream(
						ImmutableTreeVector<CumulusWorkerEvent> eventStream,
						bool validateResponses
						)
			{
			PolymorphicSharedPtr<CumulusWorkerEventSimulator> sim(
				new CumulusWorkerEventSimulator(validateResponses)
				);

			for (auto event: eventStream)
				sim->handleEvent(event);

			lassert(sim->finishedSuccessfully());
			}

		static void replayCumulusWorkerEventStreamFromFile(std::string filename, bool validateResponses)
			{
			PolymorphicSharedPtr<CumulusWorkerEventSimulator> sim(
				new CumulusWorkerEventSimulator(validateResponses)
				);

			FILE* f = fopen(filename.c_str(),"rb");

			lassert_dump(f, "couldn't open " << filename);
			
			IFileProtocol protocol(f);

			IBinaryStream stream(protocol);

			SerializedObjectInflater inflater;

			SerializedObjectInflaterDeserializer deserializer(
				inflater, 
				stream,
				PolymorphicSharedPtr<VectorDataMemoryManager>()
				);

			while (true)
				{
				Cumulus::CumulusWorkerEvent event;
	
				try {
					deserializer.deserialize(event);
					}
				catch(...)
					{
					break;
					}

				sim->handleEvent(event);
				}

			lassert(sim->finishedSuccessfully());
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			def("replayCumulusWorkerEventStream", replayCumulusWorkerEventStream);
			def("replayCumulusWorkerEventStreamFromFile", replayCumulusWorkerEventStreamFromFile);
			}

};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<CumulusWorkerEventSimulatorWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			CumulusWorkerEventSimulatorWrapper>::registerWrapper();




