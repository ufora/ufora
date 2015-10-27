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
#include "CumulusWorker.hppml"


#include <stdint.h>
#include <boost/python.hpp>
#include "../networking/SerializedChannel.hpp"
#include "../networking/MultiChannel.hpp"
#include "../networking/OrderedMessage.hppml"
#include "../core/python/ScopedPyThreads.hpp"
#include "../core/python/CPPMLWrapper.hpp"
#include "../core/threading/CallbackSchedulerFactory.hppml"
#include "../native/Registrar.hpp"
#include "../core/PolymorphicSharedPtrBinder.hpp"
#include "../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"
#include "../networking/SerializedChannel.hpp"
#include "../FORA/Core/ExecutionContextConfiguration.hppml"
#include "../FORA/Serialization/SerializedObjectFlattener.hpp"
#include "../FORA/Serialization/SerializedObjectFlattenerStream.hpp"
#include "CumulusWorkerToWorkerMessage.hppml"
#include "CumulusClientToWorkerMessage.hppml"
#include "CumulusWorkerToClientMessage.hppml"
#include "CumulusWorkerEventHandler/EventHandler.hppml"

#include "../networking/Channel.py.hpp"
#include "../networking/HalfChannel.hpp"

using namespace Cumulus;

typedef Channel<
			OrderedMessage<CumulusWorkerToWorkerMessage>,
			OrderedMessage<CumulusWorkerToWorkerMessage>
		> ordered_worker_to_worker_channel_type;

typedef Channel<
			OrderedMessage<CumulusWorkerToClientMessage>,
			OrderedMessage<CumulusClientToWorkerMessage>
		> ordered_worker_to_client_channel_type;

typedef SerializedChannel<
			OrderedMessage<CumulusWorkerToWorkerMessage>,
			OrderedMessage<CumulusWorkerToWorkerMessage>,
			SerializedObjectFlattenerSerializer,
			SerializedObjectInflaterDeserializer
			> serialized_worker_to_worker_channel_type;

typedef MultiChannel<
			CumulusWorkerToWorkerMessage,
			CumulusWorkerToWorkerMessage
			> worker_to_worker_multi_channel_type;

typedef SerializedChannel<
			OrderedMessage<CumulusWorkerToClientMessage>,
			OrderedMessage<CumulusClientToWorkerMessage>,
			SerializedObjectFlattenerSerializer,
			SerializedObjectInflaterDeserializer
			> serialized_worker_to_client_channel_type;

typedef MultiChannel<
			CumulusWorkerToClientMessage,
			CumulusClientToWorkerMessage
			> worker_to_client_multi_channel_type;

typedef Channel<
			Cumulus::PythonIoTaskResponse,
			Cumulus::PythonIoTaskRequest
			> dataset_load_channel_type;

typedef HalfChannel<
			Cumulus::PythonIoTaskResponse,
			Cumulus::PythonIoTaskRequest
			> dataset_load_half_channel_type;

typedef dataset_load_half_channel_type::pointer_type dataset_load_half_channel_ptr_type;

typedef dataset_load_channel_type::pointer_type dataset_load_channel_ptr_type;

typedef ChannelWrapper<
			Cumulus::PythonIoTaskResponse,
			Cumulus::PythonIoTaskRequest
			> dataset_load_channel_wrapper_type;

typedef CumulusWorkerEventHandler::EventHandler::pointer_type event_handler_pointer_type;

class CumulusWorkerWrapper :
		public native::module::Exporter<CumulusWorkerWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "Cumulus";
			}

		void	getDefinedTypes(std::vector<std::string>& outTypes)
			{
			outTypes.push_back(typeid(PolymorphicSharedPtr<CumulusWorker>).name());
			}

		static PolymorphicSharedPtr<CumulusWorker>* constructCumulusWorker(
						PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
						CumulusWorkerConfiguration inWorkerConfiguration,
						PolymorphicSharedPtr<VectorDataManager> inVDM,
						PolymorphicSharedPtr<OfflineCache> inOfflineCache,
						event_handler_pointer_type inEventHandler
						)
			{
			return new PolymorphicSharedPtr<CumulusWorker>(
				new CumulusWorker(
					inCallbackScheduler->getFactory(),
					inCallbackScheduler,
					inWorkerConfiguration,
					inVDM,
					inOfflineCache,
					boost::bind(
						boost::function2<void, event_handler_pointer_type, CumulusWorkerEvent>(
							[](event_handler_pointer_type handler,
									CumulusWorkerEvent event) {
								handler->handleEvent(event);
								}
							),
						inEventHandler,
						boost::arg<1>()
						)
					)
				);
			}

		static PolymorphicSharedPtr<CumulusWorker>* constructCumulusWorker2(
						PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
						CumulusWorkerConfiguration workerConfiguration,
						PolymorphicSharedPtr<VectorDataManager> inVDM,
						PolymorphicSharedPtr<OfflineCache> inOfflineCache
						)
			{
			return new PolymorphicSharedPtr<CumulusWorker>(
				new CumulusWorker(
					inCallbackScheduler->getFactory(),
					inCallbackScheduler,
					workerConfiguration,
					inVDM,
					inOfflineCache,
					boost::function1<void, CumulusWorkerEvent>()
					)
				);
			}

		typedef PolymorphicSharedPtr<Channel<std::string, std::string>> string_channel_ptr;


		template <class message_type>
		static uint32_t getMessagePriority(message_type message)
			{
			return message.priority();
			}


		static void addMachine(
				PolymorphicSharedPtr<CumulusWorker> worker,
				MachineId machine,
				boost::python::list& channels,
				ImplValContainer& inBuiltins,
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
				)
			{
			lassert(boost::python::len(channels) == 2);
			std::vector<serialized_worker_to_worker_channel_type::pointer_type> serializedChannels1;
			serializedChannels1.reserve(boost::python::len(channels));

			PolymorphicSharedPtr<CallbackScheduler> subScheduler = 
				inCallbackScheduler->getFactory()->createScheduler("SocketConnectionTo_" + prettyPrintString(machine));

			for (int i = 0, len = boost::python::len(channels); i < len; i++)
				{
				string_channel_ptr stringChannel = 
					boost::python::extract<string_channel_ptr>(channels[i])();

				stringChannel->setCallbackScheduler(subScheduler);
				
				serialized_worker_to_worker_channel_type::pointer_type channelPtr(
					new serialized_worker_to_worker_channel_type(
						subScheduler,
						stringChannel
						)
					);
				serializedChannels1.push_back(channelPtr);
				}

			ScopedPyThreads releaseTheGil;

			std::vector<ordered_worker_to_worker_channel_type::pointer_type> serializedChannels2;

			for (auto channelPtr: serializedChannels1)
				{
				channelPtr->getSerializer().getSerializer().getFlattener().considerValueAlreadyWritten(inBuiltins);
				channelPtr->getDeserializer().getDeserializer().getInflater().considerValueAlreadyRead(inBuiltins);
				channelPtr->getDeserializer().getDeserializer().setVDMM(worker->getVDM()->getMemoryManager());

				serializedChannels2.push_back(channelPtr);
				}

			worker_to_worker_multi_channel_type::pointer_type multiChannel(
					new worker_to_worker_multi_channel_type(
						serializedChannels2,
						&CumulusWorkerWrapper::getMessagePriority<CumulusWorkerToWorkerMessage>,
						subScheduler
						)
					);

			worker->addMachine(
				machine,
				worker_to_worker_channel_ptr_type(multiChannel)
				);
			}

		static void dropMachine(
				PolymorphicSharedPtr<CumulusWorker> worker,
				MachineId machine
				)
			{
			ScopedPyThreads releaseTheGil;

			worker->dropMachine(machine);
			}

		static void addCumulusClient(
				PolymorphicSharedPtr<CumulusWorker> worker,
				CumulusClientId clientId,
				boost::python::list& channels,
				ImplValContainer& inBuiltins,
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
				)
			{
			lassert(boost::python::len(channels) == 2);
			std::vector<serialized_worker_to_client_channel_type::pointer_type> serializedChannels1;
			serializedChannels1.reserve(boost::python::len(channels));
			for (int i = 0, len = boost::python::len(channels); i < len; i++)
				{
				serialized_worker_to_client_channel_type::pointer_type channelPtr(
					new serialized_worker_to_client_channel_type(
						inCallbackScheduler,
						boost::python::extract<string_channel_ptr>(channels[i])()
						)
					);

				serializedChannels1.push_back(channelPtr);
				}

			ScopedPyThreads releaseTheGil;

			std::vector<ordered_worker_to_client_channel_type::pointer_type> serializedChannels2;

			for (auto channelPtr: serializedChannels1)
				{
				channelPtr->getSerializer().getSerializer().getFlattener().considerValueAlreadyWritten(inBuiltins);
				channelPtr->getDeserializer().getDeserializer().getInflater().considerValueAlreadyRead(inBuiltins);
				channelPtr->getDeserializer().getDeserializer().setVDMM(worker->getVDM()->getMemoryManager());

				serializedChannels2.push_back(channelPtr);
				}

			worker_to_client_multi_channel_type::pointer_type multiChannel(
					new worker_to_client_multi_channel_type(
						serializedChannels2,
						&CumulusWorkerWrapper::getMessagePriority<CumulusWorkerToClientMessage>,
						inCallbackScheduler
						)
					);

			worker->addCumulusClient(
				clientId, 
				worker_to_client_channel_ptr_type(multiChannel)
				);
			}

		static void nullDisconnectFunction(void)
			{
			}

		static boost::python::object getGlobalScheduler(PolymorphicSharedPtr<CumulusWorker> worker)
			{
			auto scheduler = worker->getGlobalScheduler();

			if (!scheduler)
				return boost::python::object();
			else
				return boost::python::object(scheduler);
			}

		static dataset_load_channel_ptr_type
		getExternalDatasetRequestChannel(
								PolymorphicSharedPtr<CumulusWorker> worker,
								PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
								)
			{
			dataset_load_half_channel_ptr_type channel(
				new HalfChannel<
						Cumulus::PythonIoTaskResponse,
						Cumulus::PythonIoTaskRequest
						>(
					inCallbackScheduler,
					boost::bind(
						PolymorphicSharedPtrBinder::memberFunctionToWeakPtrFunction(
							&CumulusWorker::handlePythonIoTaskResponse
							),
						worker->polymorphicSharedWeakPtrFromThis(),
						boost::arg<1>()
						),
					nullDisconnectFunction
					)
				);

			worker->onPythonIoTaskRequest().subscribe(
				dataset_load_half_channel_type::weak_ptr_type(channel),
				&dataset_load_half_channel_type::receive
				);

			return channel;
			}

		static void teardown(PolymorphicSharedPtr<CumulusWorker> worker)
			{
			ScopedPyThreads releaseTheGil;

			worker->teardown();
			}

		static boost::python::object getRegimeHash(PolymorphicSharedPtr<CumulusWorker> worker)
			{
			Nullable<hash_type> hash = worker->currentRegimeHash();

			if (!hash)
				return boost::python::object();

			return boost::python::object(*hash);
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			class_<PolymorphicSharedPtr<CumulusWorker> >("CumulusWorker", no_init)
				.def("__init__", make_constructor(constructCumulusWorker))
				.def("__init__", make_constructor(constructCumulusWorker2))
				.def("startComputations", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(CumulusWorker::startComputations)
						)
				.def("teardown", teardown)
				.def("addMachine", addMachine)
				.def("dropMachine", dropMachine)
				.def("addCumulusClient", addCumulusClient)
				.def("dropCumulusClient", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(CumulusWorker::dropCumulusClient)
						)
				.def("getExternalDatasetRequestChannel", 
						getExternalDatasetRequestChannel
						)
				.def("getSystemwidePageRefcountTracker", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(
							CumulusWorker::getSystemwidePageRefcountTracker
							)
						)
				.def("triggerRegimeChange", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(
							CumulusWorker::triggerRegimeChange
							)
						)
				.def("getRegimeHash", &getRegimeHash)
				.def("hasEstablishedHandshakeWithExistingMachines", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(
							CumulusWorker::hasEstablishedHandshakeWithExistingMachines
							)
						)
				.def("currentlyActiveWorkerThreads", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(
							CumulusWorker::currentlyActiveWorkerThreads
							)
						)
				.def("getLocalScheduler", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(
							CumulusWorker::getLocalScheduler
							)
						)
				.def("dumpStateToLog", 
						macro_polymorphicSharedPtrFuncFromMemberFunc(
							CumulusWorker::dumpStateToLog
							)
						)
				.def("getGlobalScheduler", getGlobalScheduler)
				;

			Ufora::python::CPPMLWrapper<CumulusCheckpointPolicy>
				("CumulusCheckpointPolicy", false).class_();

			Ufora::python::CPPMLWrapper<CumulusWorkerConfiguration>
				("CumulusWorkerConfiguration", false).class_();
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<CumulusWorkerWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<CumulusWorkerWrapper>::registerWrapper();

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<dataset_load_channel_wrapper_type>::mEnforceRegistration =
				native::module::ExportRegistrar<dataset_load_channel_wrapper_type>
					::registerWrapper("CumulusWorkerExternalDatasetChannel");



