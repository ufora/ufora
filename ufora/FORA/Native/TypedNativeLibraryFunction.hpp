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

#include "TypedNativeExpression.hppml"
#include <boost/type_traits.hpp>

template<class T>
class is_pass_by_register_type {
public:
	const static bool value;
};

template<class T>
const bool is_pass_by_register_type<T>::value = 
		boost::has_trivial_destructor<T>::value && 
		boost::has_trivial_copy_constructor<T>::value
		;

template<class T>
class is_pass_by_register_type<T&> {
public:
	const static bool value;
};

template<class T>
const bool is_pass_by_register_type<T&>::value = true;

NativeExpression callLibraryFunctionContainingCPPTypes(
			NativeLibraryFunctionTarget target,
			NativeType resultType,
			bool resultTypeIsPOD,
			ImmutableTreeVector<NativeExpression> inArguments,
			ImmutableTreeVector<bool> inArgumentTypesArePOD
			);

template<class return_type>
class TypedNativeLibraryFunction0 {
public:
	typedef return_type (*fun_ptr_type)();

	TypedNativeLibraryFunction0(fun_ptr_type inPtr) : mFunPtr(inPtr)
		{
		}

	TypedNativeExpression<return_type> operator()() const
		{
		return TypedNativeExpression<return_type>(
			callLibraryFunctionContainingCPPTypes(
				NativeLibraryFunctionTarget::ByPointer( (uword_t)mFunPtr ),
				NativeTypeFor<return_type>::get(),
				is_pass_by_register_type<return_type>::value,
				emptyTreeVec(),
				emptyTreeVec()
				)
			);
		}

private:
	fun_ptr_type mFunPtr;
};


template<class return_type, class A1>
class TypedNativeLibraryFunction1 {
public:
	typedef return_type (*fun_ptr_type)(A1);

	TypedNativeLibraryFunction1(fun_ptr_type inPtr) : mFunPtr(inPtr)
		{
		}

	TypedNativeExpression<return_type> operator()(TypedNativeExpression<A1> a1) const
		{
		return TypedNativeExpression<return_type>(
			callLibraryFunctionContainingCPPTypes(
				NativeLibraryFunctionTarget::ByPointer( (uword_t)mFunPtr ),
				NativeTypeFor<return_type>::get(),
				is_pass_by_register_type<return_type>::value,
				emptyTreeVec() + 
					a1.getExpression(),
				emptyTreeVec() + 
					is_pass_by_register_type<A1>::value
				)
			);
		}

private:
	fun_ptr_type mFunPtr;
};



template<class return_type, class A1, class A2>
class TypedNativeLibraryFunction2 {
public:
	typedef return_type (*fun_ptr_type)(A1, A2);

	TypedNativeLibraryFunction2(fun_ptr_type inPtr) : mFunPtr(inPtr)
		{
		}

	TypedNativeExpression<return_type> operator()(
							TypedNativeExpression<A1> a1,
							TypedNativeExpression<A2> a2
							) const
		{
		return TypedNativeExpression<return_type>(
			callLibraryFunctionContainingCPPTypes(
				NativeLibraryFunctionTarget::ByPointer( (uword_t)mFunPtr ),
				NativeTypeFor<return_type>::get(),
				is_pass_by_register_type<return_type>::value,
				emptyTreeVec() + 
					a1.getExpression() + 
					a2.getExpression(),
				emptyTreeVec() + 
					is_pass_by_register_type<A1>::value + 
					is_pass_by_register_type<A2>::value
				)
			);
		}

private:
	fun_ptr_type mFunPtr;
};


template<class return_type, class A1, class A2, class A3>
class TypedNativeLibraryFunction3 {
public:
	typedef return_type (*fun_ptr_type)(A1, A2, A3);

	TypedNativeLibraryFunction3(fun_ptr_type inPtr) : mFunPtr(inPtr)
		{
		}

	TypedNativeExpression<return_type> operator()(
							TypedNativeExpression<A1> a1,
							TypedNativeExpression<A2> a2,
							TypedNativeExpression<A3> a3
							) const
		{
		return TypedNativeExpression<return_type>(
			callLibraryFunctionContainingCPPTypes(
				NativeLibraryFunctionTarget::ByPointer( (uword_t)mFunPtr ),
				NativeTypeFor<return_type>::get(),
				is_pass_by_register_type<return_type>::value,
				emptyTreeVec() + 
					a1.getExpression() + 
					a2.getExpression() + 
					a3.getExpression(),
				emptyTreeVec() + 
					is_pass_by_register_type<A1>::value + 
					is_pass_by_register_type<A2>::value + 
					is_pass_by_register_type<A3>::value
				)
			);
		}

private:
	fun_ptr_type mFunPtr;
};

template<class return_type, class A1, class A2, class A3, class A4>
class TypedNativeLibraryFunction4 {
public:
	typedef return_type (*fun_ptr_type)(A1, A2, A3, A4);

	TypedNativeLibraryFunction4(fun_ptr_type inPtr) : mFunPtr(inPtr)
		{
		}

	TypedNativeExpression<return_type> operator()(
							TypedNativeExpression<A1> a1,
							TypedNativeExpression<A2> a2,
							TypedNativeExpression<A3> a3,
							TypedNativeExpression<A4> a4
							) const
		{
		return TypedNativeExpression<return_type>(
			callLibraryFunctionContainingCPPTypes(
				NativeLibraryFunctionTarget::ByPointer( (uword_t)mFunPtr ),
				NativeTypeFor<return_type>::get(),
				is_pass_by_register_type<return_type>::value,
				emptyTreeVec() + 
					a1.getExpression() + 
					a2.getExpression() + 
					a3.getExpression() + 
					a4.getExpression(),
				emptyTreeVec() + 
					is_pass_by_register_type<A1>::value + 
					is_pass_by_register_type<A2>::value + 
					is_pass_by_register_type<A3>::value + 
					is_pass_by_register_type<A4>::value
				)
			);
		}

private:
	fun_ptr_type mFunPtr;
};

template<class return_type, class A1, class A2, class A3, class A4, class A5>
class TypedNativeLibraryFunction5 {
public:
	typedef return_type (*fun_ptr_type)(A1, A2, A3, A4, A5);

	TypedNativeLibraryFunction5(fun_ptr_type inPtr) : mFunPtr(inPtr)
		{
		}

	TypedNativeExpression<return_type> operator()(
							TypedNativeExpression<A1> a1,
							TypedNativeExpression<A2> a2,
							TypedNativeExpression<A3> a3,
							TypedNativeExpression<A4> a4,
							TypedNativeExpression<A5> a5
							) const
		{
		return TypedNativeExpression<return_type>(
			callLibraryFunctionContainingCPPTypes(
				NativeLibraryFunctionTarget::ByPointer( (uword_t)mFunPtr ),
				NativeTypeFor<return_type>::get(),
				is_pass_by_register_type<return_type>::value,
				emptyTreeVec() + 
					a1.getExpression() + 
					a2.getExpression() + 
					a3.getExpression() + 
					a4.getExpression() +
					a5.getExpression(),
				emptyTreeVec() + 
					is_pass_by_register_type<A1>::value + 
					is_pass_by_register_type<A2>::value + 
					is_pass_by_register_type<A3>::value + 
					is_pass_by_register_type<A4>::value +
					is_pass_by_register_type<A5>::value
				)
			);
		}

private:
	fun_ptr_type mFunPtr;
};




template<class return_type>
TypedNativeLibraryFunction0<return_type> 
					makeTypedNativeLibraryFunction(return_type (*funPtr)())
	{
	return TypedNativeLibraryFunction0<return_type>(funPtr);
	}

template<class return_type, class A1>
TypedNativeLibraryFunction1<return_type, A1> 
					makeTypedNativeLibraryFunction(return_type (*funPtr)(A1))
	{
	return TypedNativeLibraryFunction1<return_type, A1>(funPtr);
	}

template<class return_type, class A1, class A2>
TypedNativeLibraryFunction2<return_type, A1, A2> 
					makeTypedNativeLibraryFunction(return_type (*funPtr)(A1, A2))
	{
	return TypedNativeLibraryFunction2<return_type, A1, A2>(funPtr);
	}

template<class return_type, class A1, class A2, class A3>
TypedNativeLibraryFunction3<return_type, A1, A2, A3> 
					makeTypedNativeLibraryFunction(return_type (*funPtr)(A1, A2, A3))
	{
	return TypedNativeLibraryFunction3<return_type, A1, A2, A3>(funPtr);
	}

template<class return_type, class A1, class A2, class A3, class A4>
TypedNativeLibraryFunction4<return_type, A1, A2, A3, A4> 
					makeTypedNativeLibraryFunction(return_type (*funPtr)(A1, A2, A3, A4))
	{
	return TypedNativeLibraryFunction4<return_type, A1, A2, A3, A4>(funPtr);
	}

template<class return_type, class A1, class A2, class A3, class A4, class A5>
TypedNativeLibraryFunction5<return_type, A1, A2, A3, A4, A5> 
makeTypedNativeLibraryFunction(return_type (*funPtr)(A1, A2, A3, A4, A5))
	{
	return TypedNativeLibraryFunction5<return_type, A1, A2, A3, A4, A5>(funPtr);
	}


