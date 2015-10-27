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
#include "CpuAssignmentDependencyGraph.hpp"
#include "CumulusClient.hppml"

#include <stdint.h>
#include <boost/python.hpp>
#include "../core/threading/Queue.hpp"
#include "../core/python/ScopedPyThreads.hpp"
#include "../core/python/CPPMLWrapper.hpp"
#include "../native/Registrar.hpp"
#include "../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"

using namespace Cumulus;

class CpuAssignmentDependencyGraphWrapper :
		public native::module::Exporter<CpuAssignmentDependencyGraphWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "Cumulus";
			}

		void	getDefinedTypes(std::vector<std::string>& outTypes)
			{
			outTypes.push_back(typeid(PolymorphicSharedPtr<CpuAssignmentDependencyGraph>).name());
			}

		static PolymorphicSharedPtr<CpuAssignmentDependencyGraph>* constructCpuAssignmentDependencyGraph(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				PolymorphicSharedPtr<VectorDataManager> inVDM
				)
			{
			return new PolymorphicSharedPtr<CpuAssignmentDependencyGraph>(
				new CpuAssignmentDependencyGraph(inCallbackScheduler, inVDM)
				);
			}

		class CpuAssignmentDependencyGraphListener : 
				public PolymorphicSharedPtrBase<CpuAssignmentDependencyGraphListener> {
		public:
			CpuAssignmentDependencyGraphListener(PolymorphicSharedPtr<CpuAssignmentDependencyGraph> inGraph) : 
					mGraph(inGraph)
				{
				}

			void polymorphicSharedPtrBaseInitialized()
				{
				mGraph->onCpuAssignmentChanged().subscribe(
					polymorphicSharedWeakPtrFromThis(),
					&CpuAssignmentDependencyGraphListener::changed
					);
				}

			boost::python::object get()
				{
				ComputationSystemwideCpuAssignment e;

					{
					ScopedPyThreads releaseTheGil;
				
					e = mAssignments.get();
					}

				return boost::python::object(e);
				}

			boost::python::object getNonblock()
				{
				Nullable<ComputationSystemwideCpuAssignment> e;

					{
					ScopedPyThreads releaseTheGil;

					e = mAssignments.getNonblock();
					}


				if (e)
					return boost::python::object(*e);

				return boost::python::object();
				}

			boost::python::object getTimeout(double t)
				{
				ComputationSystemwideCpuAssignment e;
					
					{
					ScopedPyThreads releaseTheGil;
					
					if (!mAssignments.getTimeout(e, t))
						return boost::python::object();
					}

				return boost::python::object(e);
				}

			Queue<ComputationSystemwideCpuAssignment> mAssignments;

			void changed(ComputationSystemwideCpuAssignment msg)
				{
				mAssignments.write(msg);
				}

			PolymorphicSharedPtr<CpuAssignmentDependencyGraph> mGraph;
		};

		static PolymorphicSharedPtr<CpuAssignmentDependencyGraphListener> createListener(
									PolymorphicSharedPtr<CpuAssignmentDependencyGraph> client
									)
			{
			return PolymorphicSharedPtr<CpuAssignmentDependencyGraphListener>(
				new CpuAssignmentDependencyGraphListener(
					client
					)
				);
			}

		static void updateDependencyGraph(PolymorphicSharedPtr<CpuAssignmentDependencyGraph> graph)
			{
			ScopedPyThreads releaseTheGil;
			
			graph->updateDependencyGraph();
			}

		static void subscribeToCumulusClient(
								PolymorphicSharedPtr<CpuAssignmentDependencyGraph> graph,
								PolymorphicSharedPtr<CumulusClient> client
								)
			{
			client->onRootToRootDependencyCreated().subscribe(
				graph->polymorphicSharedWeakPtrFromThis(),
				&CpuAssignmentDependencyGraph::handleRootToRootDependencyCreated
				);
			
			client->onRootComputationComputeStatusChanged().subscribe(
				graph->polymorphicSharedWeakPtrFromThis(),
				&CpuAssignmentDependencyGraph::handleRootComputationComputeStatusChanged
				);
			
			client->onCheckpointStatusUpdateMessage().subscribe(
				graph->polymorphicSharedWeakPtrFromThis(),
				&CpuAssignmentDependencyGraph::handleCheckpointStatusUpdateMessage
				);

			client->onWorkerAdd().subscribe(
				graph->polymorphicSharedWeakPtrFromThis(),
				&CpuAssignmentDependencyGraph::addMachine
				);
			
			client->onWorkerDrop().subscribe(
				graph->polymorphicSharedWeakPtrFromThis(),
				&CpuAssignmentDependencyGraph::dropMachine
				);

			client->onComputationIsCurrentlyCheckpointing().subscribe(
				graph->polymorphicSharedWeakPtrFromThis(),
				&CpuAssignmentDependencyGraph::handleComputationIsCurrentlyCheckpointing
				);
			}

		static uint64_t computeBytecountForHashes(
								PolymorphicSharedPtr<CpuAssignmentDependencyGraph> graph,
								ImmutableTreeSet<hash_type> hashes
								)
			{
			ScopedPyThreads releaseTheGil;
						
			return graph->computeBytecountForHashes(hashes);
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			class_<PolymorphicSharedPtr<CpuAssignmentDependencyGraphListener> >("CpuAssignmentDependencyGraphListener", no_init)
				.def("get", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(CpuAssignmentDependencyGraphListener::get)
						)
				.def("getNonblock", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(CpuAssignmentDependencyGraphListener::getNonblock)
						)
				.def("getTimeout", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(CpuAssignmentDependencyGraphListener::getTimeout)
						)
				;

			class_<PolymorphicSharedPtr<CpuAssignmentDependencyGraph> >("CpuAssignmentDependencyGraph", no_init)
				.def("__init__", make_constructor(constructCpuAssignmentDependencyGraph))
				.def("subscribeToCumulusClient", 
						subscribeToCumulusClient
						)
				.def("updateDependencyGraph", updateDependencyGraph)
				.def("markRootComputation", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(CpuAssignmentDependencyGraph::markRootComputation)
						)
				.def("markNonrootComputation", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(CpuAssignmentDependencyGraph::markNonrootComputation)
						)
				.def("createListener", 
						createListener
						)
				.def("computeBytecountForHashes", 
						computeBytecountForHashes
						)
				;
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<CpuAssignmentDependencyGraphWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<CpuAssignmentDependencyGraphWrapper>::registerWrapper();


