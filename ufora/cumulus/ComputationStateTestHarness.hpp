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

#include "../core/UnitTest.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "ComputationState.hppml"
#include "../FORA/Core/ExecutionContextConfiguration.hppml"
#include "../FORA/Serialization/SerializedObject.hpp"

namespace Cumulus {

class ComputationStateTestHarness {
public:
	ComputationStateTestHarness() :
			mCallbackScheduler(CallbackScheduler::singletonForTesting()),
			mVdmMemorySize(10 * 1024 * 1024),
			mVdm(new VectorDataManager(mCallbackScheduler, mVdmMemorySize))
		{
		}

	ComputationStateTestHarness(PolymorphicSharedPtr<VectorDataManager> inVDM) :
			mVdmMemorySize(10 * 1024 * 1024),
			mVdm(inVDM)
		{
		}

	PolymorphicSharedPtr<ComputationState> deepcopyComputationState(PolymorphicSharedPtr<ComputationState> state)
		{
		PolymorphicSharedPtr<ComputationState> newState(
			new ComputationState(
				state->ownComputationId(),
				mVdm,
				Fora::Interpreter::ExecutionContextConfiguration::defaultConfig(),
				mCallbackScheduler
				)
			);

		newState->deserialize(state->serialize());

		return newState;
		}

	void resetVdm()
		{
		mVdm.reset(new VectorDataManager(mCallbackScheduler, mVdmMemorySize));
		}

	static ExternalIoTaskId newExternalIOTask(ExternalIoTask)
		{
		return ExternalIoTaskId(RandomHashGenerator::singleton().generateRandomHash());
		}

	static ComputationId newComputation(map<ComputationId, ComputationDefinition>* outComputations, ComputationDefinition threadDef)
		{
		ComputationId newComputation =
			ComputationId::CreateIdForRootOnWorker(
				threadDef,
				RandomHashGenerator::singleton().generateRandomHash()
				);

		(*outComputations)[newComputation] = threadDef;

		return newComputation;
		}

	ImplValContainer assertIsFinished(PolymorphicSharedPtr<ComputationState> state)
		{
		lassert(state->currentComputationStatus().isFinished());

		Nullable<Fora::Interpreter::ComputationResult> result = state->getResult();

		lassert(result);
		lassert_dump(result->isResult(), prettyPrintString(result));

		return(result->getResult().result());
		}

	Fora::Interpreter::ComputationResult computeSimple(
			const ComputationDefinition& def
			)
		{
		PolymorphicSharedPtr<ComputationState> state(
			new ComputationState(
				ComputationId::CreateIdForRootOnWorker(
					def,
					RandomHashGenerator::singleton().generateRandomHash()
					),
				mVdm,
				Fora::Interpreter::ExecutionContextConfiguration::defaultConfig(),
				mCallbackScheduler
				)
			);

		lassert(state->currentComputationStatus().isUninitialized());

		state->initialize(def);

		while (!state->currentComputationStatus().isFinished())
			{
			CreatedComputations threadsCreated;

			threadsCreated = state->compute(mVdm->newVectorHash());

			for (auto it = threadsCreated.computations().begin(); it != threadsCreated.computations().end(); it++)
				state->addComputationResult(
					ComputationResult(
						it->first,
						SerializedObject::serialize(
							computeSimple(it->second),
							mVdm->getMemoryManager()
							),
						state->currentComputationStatistics()
						)
					);
			}

		Nullable<Fora::Interpreter::ComputationResult> result = state->getResult();

		lassert(result);

		return *result;
		}

	//use ComputationState to do a simple FORA apply.
	ImplValContainer calculateSimple(
			const ImplValContainer& args,
			const bool keepalive = false
			)
		{
		return calculateSimple(
			ComputationDefinition::Root(
				ComputationDefinitionTerm::ApplyFromTuple(args)
				),
			keepalive
			);
		}

	ImplValContainer calculateSimple(
			const ComputationDefinition& def,
			const bool keepalive = false
			)
		{
		PolymorphicSharedPtr<ComputationState> state(
			new ComputationState(
				ComputationId::CreateIdForRootOnWorker(
					def,
					RandomHashGenerator::singleton().generateRandomHash()
					),
				mVdm,
				Fora::Interpreter::ExecutionContextConfiguration::defaultConfig(),
				mCallbackScheduler
				)
			);

		lassert(state->currentComputationStatus().isUninitialized());

		state->initialize(def);

		lassert_dump(
			state->currentComputationStatus().isComputableWithSubcomputations(),
			prettyPrintString(state->currentComputationStatus())
			);

		CreatedComputations threadsCreated;

		threadsCreated = state->compute(mVdm->newVectorHash());

		lassert(threadsCreated.isEmpty());

		if (keepalive)
			mComputationStatesToKeepAlive.push_back(state);

		return assertIsFinished(state);
		}

	ImplValContainer calculateSimple(
			ImmutableTreeVector<ImplValContainer> vals,
			const bool keepalive = false
			)
		{
		return calculateSimple(ImplValContainer(vals), keepalive);
		}

	//evaluate an expression
	ImplValContainer evaluate(
			const std::string& inValue,
			const bool keepalive = false
			)
		{
		ImplValContainer binder = calculateSimple(
			emptyTreeVec() +
				ImplValContainer(CSTValue(Symbol("Function"))) +
				ImplValContainer(CSTValue(Symbol("Call"))) +
				ImplValContainer(CSTValue(inValue)),
			keepalive
			);

		return calculateSimple(
			emptyTreeVec() + binder + ImplValContainer(CSTValue(Symbol("Call"))),
			keepalive
			);
		}

	ImplValContainer evaluateAndKeepAlive(
			const std::string& inValue
			)
		{
		return evaluate(inValue, true);
		}

	PolymorphicSharedPtr<ComputationState> createComputationEvaluating(std::string inValue)
		{
		ImplValContainer binder = calculateSimple(
			emptyTreeVec() +
				ImplValContainer(CSTValue(Symbol("Function"))) +
				ImplValContainer(CSTValue(Symbol("Call"))) +
				ImplValContainer(CSTValue(inValue))
			);

		return createComputationEvaluating(
			ComputationDefinition::ApplyFromTuple(
				ImplValContainer(emptyTreeVec() +
					binder +
					ImplValContainer(CSTValue(Symbol("Call")))
					)
				)
			);
		}

	PolymorphicSharedPtr<ComputationState> createComputationEvaluating(
			const ComputationDefinition& def
			)
		{
		PolymorphicSharedPtr<ComputationState> state(
			new ComputationState(
				ComputationId::CreateIdForRootOnWorker(def, RandomHashGenerator::singleton().generateRandomHash()),
				mVdm,
				Fora::Interpreter::ExecutionContextConfiguration::defaultConfig(),
				mCallbackScheduler
				)
			);

		state->initialize(def);

		return state;
		}

	PolymorphicSharedPtr<VectorDataManager> vdm()
		{
		return mVdm;
		}

private:
	long mVdmMemorySize;

	PolymorphicSharedPtr<CallbackScheduler> mCallbackScheduler;

	PolymorphicSharedPtr<VectorDataManager> mVdm;

	std::vector<PolymorphicSharedPtr<ComputationState> > mComputationStatesToKeepAlive;
};

}


