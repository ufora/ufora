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

#include "../../core/PolymorphicSharedPtr.hpp"
#include "../../core/cppml/CPPMLPrettyPrinter.hppml"
#include "../../core/cppml/CPPMLEquality.hppml"
#include "../../core/serialization/Serialization.hpp"
#include "SerializedObject.fwd.hpp"

class SerializedObject;

template<>
class CPPMLPrettyPrint<PolymorphicSharedPtr<SerializedObject> > {
public:
		static void prettyPrint(CPPMLPrettyPrintStream& s, const PolymorphicSharedPtr<SerializedObject>& t)
			{
			streamTo(s, "SerializedObject()");
			}
};


template<class T, class T2>
class CPPMLTransform;

template<>
class CPPMLTransform<PolymorphicSharedPtr<SerializedObject>, void> {
public:
		template<class F>
		static Nullable<PolymorphicSharedPtr<SerializedObject> > apply(
							const PolymorphicSharedPtr<SerializedObject>& in,
							const F& f
							)
			{
			return null();
			}
};

template<>
class CPPMLEquality<PolymorphicSharedPtr<SerializedObject>, void> {
public:
		static char cmp(	const PolymorphicSharedPtr<SerializedObject>& lhs,
							const PolymorphicSharedPtr<SerializedObject>& rhs
							);
};


class HashingStreamSerializer;

template<>
class Serializer<SerializedObject, HashingStreamSerializer> {
public:
		static void serialize(HashingStreamSerializer& s, const SerializedObject& in);
};

template<>
class Serializer<PolymorphicSharedPtr<SerializedObject>, HashingStreamSerializer> {
public:
		static void serialize(HashingStreamSerializer& s, const PolymorphicSharedPtr<SerializedObject>& in);
};


