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

#include "../../Native/NativeTypeFor.hpp"
#include "../../Native/NativeFunctionPointer.hpp"
#include "../../Native/NativeRuntimeCallTarget.hppml"

#include "../../Axioms/ReturnValue.hpp"
#include "../../Core/MemBlockAllocator.hpp"
#include "../../Core/MemoryPool.hpp"
#include "../../../core/math/Hash.hpp"
#include "Compiler.hppml"

class TypedNativeFunctionPointerBase {
public:
	template<class T>
	static void packIntoVector(std::vector<char>& ioStack, const T& in)
		{
		long sz = ioStack.size();
		ioStack.resize(sz + sizeof(in));
		memcpy(&ioStack[sz], &in, sizeof(T));
		}

	static void packIntoVector(std::vector<char>& ioStack, const Fora::Nothing& in)
		{
		}
};

template<class fp_type>
class TypedNativeFunctionPointer {};

template<class R1>
class TypedNativeFunctionPointer<R1 (*)()> : public TypedNativeFunctionPointerBase {
public:
	TypedNativeFunctionPointer(
						const NativeFunctionPointer& inPtr,
						uword_t inEntryBlock,
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler
						) :
			mPtr(inPtr, inEntryBlock),
			mCompiler(inCompiler)
		{
		}

	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						NativeCFG inCFG,
						uword_t inEntryBlock = 0
						) :
			mCompiler(inCompiler)
		{
		initializeFromCFG(inCFG, inEntryBlock);
		}

	template<class expression_builder_type>
	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						expression_builder_type expressionBuilder
						) :
			mCompiler(inCompiler)
		{
		ImmutableTreeVector<NativeVariable> vars;

		initializeFromCFG(
			NativeCFG(
				vars,
				expressionBuilder()
				),
			0
			);
		}

	R1 operator()()
		{
		lassert(!mPtr.isEmpty());

		MemBlockAllocator allocator(4 * 1024);

		R1 toReturn;
		toReturn.~R1();

		uword_t whichContinuationWasFollowed = -1;

		std::vector<char> stackArgs;

		NativeRuntimeContinuationValue<1> args =
			mCompiler->generateDummyContinuation(
				&toReturn,
				&whichContinuationWasFollowed,
				0
				);

		packIntoVector(stackArgs, args);

		char* newStackFrame = (char*)allocator.allocate(stackArgs.size());
		memcpy(newStackFrame, &stackArgs[0], stackArgs.size());


		NativeRuntimeCallTarget target(mPtr.ptr(), mPtr.entrypoint(), newStackFrame);

		mCompiler->callFunction(target, allocator.getMemBlockPtr());

		lassert(whichContinuationWasFollowed == 0);

		return toReturn;
		}

private:
	void initializeFromCFG(NativeCFG inCFG, long inEntryBlock)
		{
		ImmutableTreeVector<NativeType> ourReturnTypes =
			emptyTreeVec() + NativeTypeFor<R1>::get();

		ImmutableTreeVector<NativeType> ourArgumentTypes;

		lassert_dump(
			inCFG.returnTypes() == ourReturnTypes,
			"native CFG had return types " << prettyPrintString(inCFG) << " but our "
				<< " signature has types " << prettyPrintString(ourReturnTypes)
			);

		lassert_dump(
			varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args()) == ourArgumentTypes,
			"native CFG had arguments "
				<< prettyPrintString(
					varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args())
					)
				<< " but our "
				<< " signature has types " << prettyPrintString(ourArgumentTypes)
			);

		std::string name = "cfg_by_hash_" + hashToString(hashValue(inCFG));

		if (!mCompiler->isDefined(name))
			mCompiler->define(name, inCFG);

		FunctionPointerHandle handle =
			mCompiler->getJumpTarget(name, NativeBlockID::external(inEntryBlock), true);

		mPtr = handle.get();
		}

	NativeFunctionPointerAndEntrypointId mPtr;

	PolymorphicSharedPtr<TypedFora::Compiler> mCompiler;
};


template<class R1, class A1>
class TypedNativeFunctionPointer<R1 (*)(A1)> : public TypedNativeFunctionPointerBase {
public:
	TypedNativeFunctionPointer(
						const NativeFunctionPointer& inPtr,
						uword_t inEntryBlock,
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler
						) :
			mPtr(inPtr, inEntryBlock),
			mCompiler(inCompiler)
		{
		}

	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						NativeCFG inCFG,
						uword_t inEntryBlock = 0
						) :
			mCompiler(inCompiler)
		{
		initializeFromCFG(inCFG, inEntryBlock);
		}

	template<class expression_builder_type>
	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						expression_builder_type expressionBuilder
						) :
			mCompiler(inCompiler)
		{
		ImmutableTreeVector<NativeVariable> vars;
		vars = vars + NativeVariable::Temp(NativeTypeFor<A1>::get());

		initializeFromCFG(
			NativeCFG(
				vars,
				expressionBuilder(vars[0].expr())
				),
			0
			);
		}

	R1 operator()(A1 a1)
		{
		lassert(!mPtr.isEmpty());

		MemBlockAllocator allocator(4 * 1024);

		R1 toReturn;
		toReturn.~R1();

		uword_t whichContinuationWasFollowed = -1;

		std::vector<char> stackArgs;

		NativeRuntimeContinuationValue<1> args =
			mCompiler->generateDummyContinuation(
				&toReturn,
				&whichContinuationWasFollowed,
				0
				);

		packIntoVector(stackArgs, args);
		packIntoVector(stackArgs, a1);

		char* newStackFrame = (char*)allocator.allocate(stackArgs.size());
		memcpy(newStackFrame, &stackArgs[0], stackArgs.size());


		NativeRuntimeCallTarget target(mPtr.ptr(), mPtr.entrypoint(), newStackFrame);

		mCompiler->callFunction(target, allocator.getMemBlockPtr());

		lassert(whichContinuationWasFollowed == 0);

		return toReturn;
		}

private:
	void initializeFromCFG(NativeCFG inCFG, long inEntryBlock)
		{
		ImmutableTreeVector<NativeType> ourReturnTypes =
			emptyTreeVec() + NativeTypeFor<R1>::get();

		ImmutableTreeVector<NativeType> ourArgumentTypes =
			emptyTreeVec() + NativeTypeFor<A1>::get();

		lassert_dump(
			inCFG.returnTypes() == ourReturnTypes,
			"native CFG had return types " << prettyPrintString(inCFG) << " but our "
				<< " signature has types " << prettyPrintString(ourReturnTypes)
			);

		lassert_dump(
			varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args()) == ourArgumentTypes,
			"native CFG had arguments "
				<< prettyPrintString(
					varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args())
					)
				<< " but our "
				<< " signature has types " << prettyPrintString(ourArgumentTypes)
			);

		std::string name = "cfg_by_hash_" + hashToString(hashValue(inCFG));

		if (!mCompiler->isDefined(name))
			mCompiler->define(name, inCFG);

		FunctionPointerHandle handle =
			mCompiler->getJumpTarget(name, NativeBlockID::external(inEntryBlock), true);

		mPtr = handle.get();
		}

	NativeFunctionPointerAndEntrypointId mPtr;

	PolymorphicSharedPtr<TypedFora::Compiler> mCompiler;
};

template<class R1, class A1, class A2>
class TypedNativeFunctionPointer<R1 (*)(A1, A2)> : public TypedNativeFunctionPointerBase {
public:
	TypedNativeFunctionPointer(
						const NativeFunctionPointer& inPtr,
						uword_t inEntryBlock,
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler
						) :
			mPtr(inPtr, inEntryBlock),
			mCompiler(inCompiler)
		{
		}

	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						NativeCFG inCFG,
						uword_t inEntryBlock = 0
						) :
			mCompiler(inCompiler)
		{
		initializeFromCFG(inCFG, inEntryBlock);
		}

	template<class expression_builder_type>
	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						expression_builder_type expressionBuilder
						) :
			mCompiler(inCompiler)
		{
		ImmutableTreeVector<NativeVariable> vars;
		vars = vars + NativeVariable::Temp(NativeTypeFor<A1>::get());
		vars = vars + NativeVariable::Temp(NativeTypeFor<A2>::get());


		initializeFromCFG(
			NativeCFG(
				vars,
				expressionBuilder(vars[0].expr(), vars[1].expr())
				),
			0
			);
		}

	R1 operator()(A1 a1, A2 a2)
		{
		lassert(!mPtr.isEmpty());

		MemBlockAllocator allocator(4 * 1024);

		R1 toReturn;
		toReturn.~R1();

		uword_t whichContinuationWasFollowed = -1;

		std::vector<char> stackArgs;

		NativeRuntimeContinuationValue<1> args =
			mCompiler->generateDummyContinuation(
				&toReturn,
				&whichContinuationWasFollowed,
				0
				);

		packIntoVector(stackArgs, args);
		packIntoVector(stackArgs, a1);
		packIntoVector(stackArgs, a2);

		char* newStackFrame = (char*)allocator.allocate(stackArgs.size());
		memcpy(newStackFrame, &stackArgs[0], stackArgs.size());


		NativeRuntimeCallTarget target(mPtr.ptr(), mPtr.entrypoint(), newStackFrame);

		mCompiler->callFunction(target, allocator.getMemBlockPtr());

		lassert(whichContinuationWasFollowed == 0);

		return toReturn;
		}

private:
	void initializeFromCFG(NativeCFG inCFG, long inEntryBlock)
		{
		ImmutableTreeVector<NativeType> ourReturnTypes =
			emptyTreeVec() + NativeTypeFor<R1>::get();

		ImmutableTreeVector<NativeType> ourArgumentTypes =
			emptyTreeVec() + NativeTypeFor<A1>::get() +
			emptyTreeVec() + NativeTypeFor<A2>::get()
			;

		lassert_dump(
			inCFG.returnTypes() == ourReturnTypes,
			"native CFG had return types " << prettyPrintString(inCFG.returnTypes()) << " but our "
				<< " signature has types " << prettyPrintString(ourReturnTypes)
			);

		lassert_dump(
			varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args()) == ourArgumentTypes,
			"native CFG had arguments "
				<< prettyPrintString(
					varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args())
					)
				<< " but our "
				<< " signature has types " << prettyPrintString(ourArgumentTypes)
			);

		std::string name = "cfg_by_hash_" + hashToString(hashValue(inCFG));

		if (!mCompiler->isDefined(name))
			mCompiler->define(name, inCFG);

		FunctionPointerHandle handle =
			mCompiler->getJumpTarget(name, NativeBlockID::external(inEntryBlock), true);

		mPtr = handle.get();
		}

	NativeFunctionPointerAndEntrypointId mPtr;

	PolymorphicSharedPtr<TypedFora::Compiler> mCompiler;
};

template<class R1, class A1, class A2, class A3>
class TypedNativeFunctionPointer<R1 (*)(A1, A2, A3)> : public TypedNativeFunctionPointerBase {
public:
	TypedNativeFunctionPointer(
						const NativeFunctionPointer& inPtr,
						uword_t inEntryBlock,
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler
						) :
			mPtr(inPtr, inEntryBlock),
			mCompiler(inCompiler)
		{
		}

	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						NativeCFG inCFG,
						uword_t inEntryBlock = 0
						) :
			mCompiler(inCompiler)
		{
		initializeFromCFG(inCFG, inEntryBlock);
		}

	template<class expression_builder_type>
	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						expression_builder_type expressionBuilder
						) :
			mCompiler(inCompiler)
		{
		ImmutableTreeVector<NativeVariable> vars;
		vars = vars + NativeVariable::Temp(NativeTypeFor<A1>::get());
		vars = vars + NativeVariable::Temp(NativeTypeFor<A2>::get());
		vars = vars + NativeVariable::Temp(NativeTypeFor<A3>::get());


		initializeFromCFG(
			NativeCFG(
				vars,
				expressionBuilder(vars[0].expr(), vars[1].expr(), vars[2].expr())
				),
			0
			);
		}

	R1 operator()(A1 a1, A2 a2, A3 a3)
		{
		lassert(!mPtr.isEmpty());

		MemBlockAllocator allocator(4 * 1024);

		R1 toReturn;
		toReturn.~R1();

		uword_t whichContinuationWasFollowed = -1;

		std::vector<char> stackArgs;

		NativeRuntimeContinuationValue<1> args =
			mCompiler->generateDummyContinuation(
				&toReturn,
				&whichContinuationWasFollowed,
				0
				);

		packIntoVector(stackArgs, args);
		packIntoVector(stackArgs, a1);
		packIntoVector(stackArgs, a2);
		packIntoVector(stackArgs, a3);

		char* newStackFrame = (char*)allocator.allocate(stackArgs.size());
		memcpy(newStackFrame, &stackArgs[0], stackArgs.size());


		NativeRuntimeCallTarget target(mPtr.ptr(), mPtr.entrypoint(), newStackFrame);

		mCompiler->callFunction(target, allocator.getMemBlockPtr());

		lassert(whichContinuationWasFollowed == 0);

		return toReturn;
		}

private:
	void initializeFromCFG(NativeCFG inCFG, long inEntryBlock)
		{
		ImmutableTreeVector<NativeType> ourReturnTypes =
			emptyTreeVec() + NativeTypeFor<R1>::get();

		ImmutableTreeVector<NativeType> ourArgumentTypes =
			emptyTreeVec() + NativeTypeFor<A1>::get() +
			emptyTreeVec() + NativeTypeFor<A2>::get() +
			emptyTreeVec() + NativeTypeFor<A3>::get()
			;

		lassert_dump(
			inCFG.returnTypes() == ourReturnTypes,
			"native CFG had return types " << prettyPrintString(inCFG) << " but our "
				<< " signature has types " << prettyPrintString(ourReturnTypes)
			);

		lassert_dump(
			varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args()) == ourArgumentTypes,
			"native CFG had arguments "
				<< prettyPrintString(
					varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args())
					)
				<< " but our "
				<< " signature has types " << prettyPrintString(ourArgumentTypes)
			);

		std::string name = "cfg_by_hash_" + hashToString(hashValue(inCFG));

		if (!mCompiler->isDefined(name))
			mCompiler->define(name, inCFG);

		FunctionPointerHandle handle =
			mCompiler->getJumpTarget(name, NativeBlockID::external(inEntryBlock), true);

		mPtr = handle.get();
		}

	NativeFunctionPointerAndEntrypointId mPtr;

	PolymorphicSharedPtr<TypedFora::Compiler> mCompiler;
};

































template<class A1>
class TypedNativeFunctionPointer<void (*)(A1)> : public TypedNativeFunctionPointerBase {
public:
	TypedNativeFunctionPointer(
						const NativeFunctionPointer& inPtr,
						uword_t inEntryBlock,
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler
						) :
			mPtr(inPtr, inEntryBlock),
			mCompiler(inCompiler)
		{
		}

	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						NativeCFG inCFG,
						uword_t inEntryBlock = 0
						) :
			mCompiler(inCompiler)
		{
		initializeFromCFG(inCFG, inEntryBlock);
		}

	template<class expression_builder_type>
	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						expression_builder_type expressionBuilder
						) :
			mCompiler(inCompiler)
		{
		ImmutableTreeVector<NativeVariable> vars;
		vars = vars + NativeVariable::Temp(NativeTypeFor<A1>::get());

		initializeFromCFG(
			NativeCFG(
				vars,
				expressionBuilder(vars[0].expr())
				),
			0
			);
		}

	void operator()(A1 a1)
		{
		lassert(!mPtr.isEmpty());

		MemBlockAllocator allocator(4 * 1024);

		uword_t whichContinuationWasFollowed = -1;

		std::vector<char> stackArgs;

		char toReturn;

		NativeRuntimeContinuationValue<1> args =
			mCompiler->generateDummyContinuation(
				&toReturn,
				&whichContinuationWasFollowed,
				0
				);

		packIntoVector(stackArgs, args);
		packIntoVector(stackArgs, a1);

		char* newStackFrame = (char*)allocator.allocate(stackArgs.size());
		memcpy(newStackFrame, &stackArgs[0], stackArgs.size());

		NativeRuntimeCallTarget target(mPtr.ptr(), mPtr.entrypoint(), newStackFrame);

		mCompiler->callFunction(target, allocator.getMemBlockPtr());

		lassert(whichContinuationWasFollowed == 0);
		}

private:
	void initializeFromCFG(NativeCFG inCFG, long inEntryBlock)
		{
		ImmutableTreeVector<NativeType> ourReturnTypes =
			emptyTreeVec() + NativeTypeFor<void>::get();

		ImmutableTreeVector<NativeType> ourArgumentTypes =
			emptyTreeVec() + NativeTypeFor<A1>::get();

		lassert_dump(
			inCFG.returnTypes() == ourReturnTypes,
			"native CFG had return types " << prettyPrintString(inCFG) << " but our "
				<< " signature has types " << prettyPrintString(ourReturnTypes)
			);

		lassert_dump(
			varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args()) == ourArgumentTypes,
			"native CFG had arguments "
				<< prettyPrintString(
					varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args())
					)
				<< " but our "
				<< " signature has types " << prettyPrintString(ourArgumentTypes)
			);

		std::string name = "cfg_by_hash_" + hashToString(hashValue(inCFG));

		if (!mCompiler->isDefined(name))
			mCompiler->define(name, inCFG);

		FunctionPointerHandle handle =
			mCompiler->getJumpTarget(name, NativeBlockID::external(inEntryBlock), true);

		mPtr = handle.get();
		}

	NativeFunctionPointerAndEntrypointId mPtr;

	PolymorphicSharedPtr<TypedFora::Compiler> mCompiler;
};

template<class A1, class A2>
class TypedNativeFunctionPointer<void (*)(A1, A2)> : public TypedNativeFunctionPointerBase {
public:
	TypedNativeFunctionPointer(
						const NativeFunctionPointer& inPtr,
						uword_t inEntryBlock,
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler
						) :
			mPtr(inPtr, inEntryBlock),
			mCompiler(inCompiler)
		{
		}

	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						NativeCFG inCFG,
						uword_t inEntryBlock = 0
						) :
			mCompiler(inCompiler)
		{
		initializeFromCFG(inCFG, inEntryBlock);
		}

	template<class expression_builder_type>
	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						expression_builder_type expressionBuilder
						) :
			mCompiler(inCompiler)
		{
		ImmutableTreeVector<NativeVariable> vars;
		vars = vars + NativeVariable::Temp(NativeTypeFor<A1>::get());
		vars = vars + NativeVariable::Temp(NativeTypeFor<A2>::get());


		initializeFromCFG(
			NativeCFG(
				vars,
				expressionBuilder(vars[0].expr(), vars[1].expr())
				),
			0
			);
		}

	void operator()(A1 a1, A2 a2)
		{
		lassert(!mPtr.isEmpty());

		MemBlockAllocator allocator(4 * 1024);

		char toReturn;

		uword_t whichContinuationWasFollowed = -1;

		std::vector<char> stackArgs;

		NativeRuntimeContinuationValue<1> args =
			mCompiler->generateDummyContinuation(
				&toReturn,
				&whichContinuationWasFollowed,
				0
				);

		packIntoVector(stackArgs, args);
		packIntoVector(stackArgs, a1);
		packIntoVector(stackArgs, a2);

		char* newStackFrame = (char*)allocator.allocate(stackArgs.size());
		memcpy(newStackFrame, &stackArgs[0], stackArgs.size());


		NativeRuntimeCallTarget target(mPtr.ptr(), mPtr.entrypoint(), newStackFrame);

		mCompiler->callFunction(target, allocator.getMemBlockPtr());

		lassert(whichContinuationWasFollowed == 0);
		}

private:
	void initializeFromCFG(NativeCFG inCFG, long inEntryBlock)
		{
		ImmutableTreeVector<NativeType> ourReturnTypes =
			emptyTreeVec() + NativeTypeFor<void>::get();

		ImmutableTreeVector<NativeType> ourArgumentTypes =
			emptyTreeVec() + NativeTypeFor<A1>::get() +
			emptyTreeVec() + NativeTypeFor<A2>::get()
			;

		lassert_dump(
			inCFG.returnTypes() == ourReturnTypes,
			"native CFG had return types " << prettyPrintString(inCFG.returnTypes()) << " but our "
				<< " signature has types " << prettyPrintString(ourReturnTypes)
			);

		lassert_dump(
			varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args()) == ourArgumentTypes,
			"native CFG had arguments "
				<< prettyPrintString(
					varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args())
					)
				<< " but our "
				<< " signature has types " << prettyPrintString(ourArgumentTypes)
			);

		std::string name = "cfg_by_hash_" + hashToString(hashValue(inCFG));

		if (!mCompiler->isDefined(name))
			mCompiler->define(name, inCFG);

		FunctionPointerHandle handle =
			mCompiler->getJumpTarget(name, NativeBlockID::external(inEntryBlock), true);

		mPtr = handle.get();
		}

	NativeFunctionPointerAndEntrypointId mPtr;

	PolymorphicSharedPtr<TypedFora::Compiler> mCompiler;
};

template<class A1, class A2, class A3>
class TypedNativeFunctionPointer<void (*)(A1, A2, A3)> : public TypedNativeFunctionPointerBase {
public:
	TypedNativeFunctionPointer(
						const NativeFunctionPointer& inPtr,
						uword_t inEntryBlock,
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler
						) :
			mPtr(inPtr, inEntryBlock),
			mCompiler(inCompiler)
		{
		}

	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						NativeCFG inCFG,
						uword_t inEntryBlock = 0
						) :
			mCompiler(inCompiler)
		{
		initializeFromCFG(inCFG, inEntryBlock);
		}

	template<class expression_builder_type>
	TypedNativeFunctionPointer(
						PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
						expression_builder_type expressionBuilder
						) :
			mCompiler(inCompiler)
		{
		ImmutableTreeVector<NativeVariable> vars;
		vars = vars + NativeVariable::Temp(NativeTypeFor<A1>::get());
		vars = vars + NativeVariable::Temp(NativeTypeFor<A2>::get());
		vars = vars + NativeVariable::Temp(NativeTypeFor<A3>::get());


		initializeFromCFG(
			NativeCFG(
				vars,
				expressionBuilder(vars[0].expr(), vars[1].expr(), vars[2].expr())
				),
			0
			);
		}

	void operator()(A1 a1, A2 a2, A3 a3)
		{
		lassert(!mPtr.isEmpty());

		MemBlockAllocator allocator(4 * 1024);

		char toReturn;

		uword_t whichContinuationWasFollowed = -1;

		std::vector<char> stackArgs;

		NativeRuntimeContinuationValue<1> args =
			mCompiler->generateDummyContinuation(
				&toReturn,
				&whichContinuationWasFollowed,
				0
				);

		packIntoVector(stackArgs, args);
		packIntoVector(stackArgs, a1);
		packIntoVector(stackArgs, a2);
		packIntoVector(stackArgs, a3);

		char* newStackFrame = (char*)allocator.allocate(stackArgs.size());
		memcpy(newStackFrame, &stackArgs[0], stackArgs.size());


		NativeRuntimeCallTarget target(mPtr.ptr(), mPtr.entrypoint(), newStackFrame);

		mCompiler->callFunction(target, allocator.getMemBlockPtr());

		lassert(whichContinuationWasFollowed == 0);
		}

private:
	void initializeFromCFG(NativeCFG inCFG, long inEntryBlock)
		{
		ImmutableTreeVector<NativeType> ourReturnTypes =
			emptyTreeVec() + NativeTypeFor<void>::get();

		ImmutableTreeVector<NativeType> ourArgumentTypes =
			emptyTreeVec() + NativeTypeFor<A1>::get() +
			emptyTreeVec() + NativeTypeFor<A2>::get() +
			emptyTreeVec() + NativeTypeFor<A3>::get()
			;

		lassert_dump(
			inCFG.returnTypes() == ourReturnTypes,
			"native CFG had return types " << prettyPrintString(inCFG) << " but our "
				<< " signature has types " << prettyPrintString(ourReturnTypes)
			);

		lassert_dump(
			varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args()) == ourArgumentTypes,
			"native CFG had arguments "
				<< prettyPrintString(
					varsToTypes(inCFG[NativeBlockID::external(inEntryBlock)].args())
					)
				<< " but our "
				<< " signature has types " << prettyPrintString(ourArgumentTypes)
			);

		std::string name = "cfg_by_hash_" + hashToString(hashValue(inCFG));

		if (!mCompiler->isDefined(name))
			mCompiler->define(name, inCFG);

		FunctionPointerHandle handle =
			mCompiler->getJumpTarget(name, NativeBlockID::external(inEntryBlock), true);

		mPtr = handle.get();
		}

	NativeFunctionPointerAndEntrypointId mPtr;

	PolymorphicSharedPtr<TypedFora::Compiler> mCompiler;
};







