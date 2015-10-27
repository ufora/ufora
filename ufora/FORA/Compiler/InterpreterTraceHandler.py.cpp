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
#include "../python/FORAPythonUtil.hppml"
#include "InterpreterTraceHandler.hppml"
#include "InterpreterTraceVisitor.hppml"
#include "InterpreterTraceTerm.hppml"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/utilities.hpp"
#include "../../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"
#include "../../native/Registrar.hpp"

#include "../../core/serialization/OFileProtocol.hpp"
#include "../../FORA/Serialization/SerializedObjectFlattener.hpp"
#include "../../core/threading/CallbackScheduler.hppml"
#include "../../core/threading/SimpleCallbackSchedulerFactory.hppml"

#include "../../core/PolymorphicSharedPtrBinder.hpp"
#include "../../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"
#include "../../core/serialization/IFileProtocol.hpp"

using namespace Ufora::python;

using namespace Fora::Interpreter;
using namespace Fora::Compiler;

namespace {


class WriteToDiskEventHandler : public PolymorphicSharedPtrBase<WriteToDiskEventHandler> {
public:
	WriteToDiskEventHandler(
				PolymorphicSharedPtr<CallbackScheduler> callbackScheduler,
				std::string filename
				) : 
			mCallbackScheduler(callbackScheduler),
			mFilename(filename)
		{
		mFile = fopen(filename.c_str(), "wb");

		lassert_dump(mFile, "failed to open " << filename);

		mFileProtocol.reset(new OFileProtocol(mFile, OFileProtocol::CloseOnDestroy::True));

		mFlattener.reset(new SerializedObjectFlattener());

		mBinaryStream.reset(new OBinaryStream(*mFileProtocol));

		mSerializer.reset(new SerializedObjectFlattenerSerializer(*mFlattener, *mBinaryStream));
		}

	void handleEvent(const ImmutableTreeVector<Fora::InterpreterTraceTerm>& event)
		{
		boost::mutex::scoped_lock lock(mMutex);

		mSerializer->serialize(event);

		mBinaryStream->flush();

		fflush(mFile);
		}

private:
	boost::mutex mMutex;

	FILE* mFile;

	PolymorphicSharedPtr<CallbackScheduler> mCallbackScheduler;

	boost::shared_ptr<OFileProtocol> mFileProtocol;

	boost::shared_ptr<OBinaryStream> mBinaryStream;

	boost::shared_ptr<SerializedObjectFlattener> mFlattener;

	boost::shared_ptr<SerializedObjectFlattenerSerializer> mSerializer;

	std::string mFilename;
};

}


class InterpreterTraceHandlerWrapper :
	public native::module::Exporter<InterpreterTraceHandlerWrapper> {
public:
	void dependencies(std::vector<std::string>& outTypes)
		{
		outTypes.push_back(typeid(Runtime).name());
		}

	std::string		getModuleName(void)
		{
		return "FORA";
		}

	static void logTracesToFile(
						PolymorphicSharedPtr<InterpreterTraceHandler> inHandler,
						std::string filename
						)
		{
		static PolymorphicSharedPtr<CallbackSchedulerFactory> factory(
				new SimpleCallbackSchedulerFactory()
				);

		static PolymorphicSharedPtr<CallbackScheduler> scheduler(
			factory->createScheduler("writeInterpreterTraceCallbackScheduler", 1)
			);

		PolymorphicSharedPtr<WriteToDiskEventHandler> eventHandler(
			new WriteToDiskEventHandler(
				scheduler,
				filename
				)
			);

		inHandler->setTraceLoggerFunction(
			boost::function1<void, ImmutableTreeVector<Fora::InterpreterTraceTerm> >(
				[=](ImmutableTreeVector<Fora::InterpreterTraceTerm> terms) {
					eventHandler->handleEvent(terms);
					}
				)
			);
		}

	static void replayTracesFromFile(
						PolymorphicSharedPtr<InterpreterTraceHandler> inHandler,
						std::string filename
						)
		{
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
			ImmutableTreeVector<Fora::InterpreterTraceTerm> event;

			try {
				deserializer.deserialize(event);
				}
			catch(...)
				{
				return;
				}

			auto visitor = inHandler->allocateTraceVisitor();

			bool sent = false;

			for (auto e: event)
				{
				visitor->addTraceTerm(e);
				if (visitor->sendTraces(true))
					{
					sent = true;
					break;
					}
				}

			lassert(sent);
			}
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;
		
		class_<PolymorphicSharedPtr<InterpreterTraceHandler> >("InterpreterTraceHandler", no_init)
			.def("logTracesToFile", &logTracesToFile)
			.def("replayTracesFromFile", &replayTracesFromFile)
			;
		}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<InterpreterTraceHandlerWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<InterpreterTraceHandlerWrapper>::registerWrapper();

