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
#include "SerializedObject.hpp"

#include <stdint.h>
#include <boost/python.hpp>
#include <boost/format.hpp>
#include "../python/FORAPythonUtil.hppml"
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/utilities.hpp"
#include "../../core/threading/ScopedThreadLocalContext.hpp"

using namespace Ufora::python;


class SerializedObjectWrapper :
	public native::module::Exporter<SerializedObjectWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "FORA";
		}
	
	void	getDefinedTypes(std::vector<std::string>& outTypes)
		{
		outTypes.push_back(typeid(PolymorphicSharedPtr<SerializedObject>).name());
		}

	static long	SerializedObjectCmp(PolymorphicSharedPtr<SerializedObject>& so1, boost::python::object& so2)
		{
		boost::python::extract<PolymorphicSharedPtr<SerializedObject>& > e(so2);
		if (e.check())
			{
			PolymorphicSharedPtr<SerializedObject> soPtr2 = e();
			
			ScopedPyThreads releaseTheGil;
		
			return so1->hash().cmp(soPtr2->hash());
			}
		return -1;
		}
		
	static long 	SerializedObjectPyHash(PolymorphicSharedPtr<SerializedObject>& so1)
		{
		ScopedPyThreads releaseTheGil;
		
		return so1->hash()[0];
		}

	static hash_type 	SerializedObjectHash(PolymorphicSharedPtr<SerializedObject>& so1)
		{
		ScopedPyThreads releaseTheGil;

		return so1->hash();
		}

	static std::string
	SerializedObjectSerializer(PolymorphicSharedPtr<SerializedObject>& inObj)
		{
		return FORAPythonUtil::serializer(inObj);
		}

	static void SerializedObjectDeserializer(
								PolymorphicSharedPtr<SerializedObject>& inObj, 
								std::string inData
								)
		{
		//we have to do some trickery because our serializers work on boost::shared_ptrs
		//and expect to be given a blank shared ptr
		PolymorphicSharedPtr<SerializedObject> toReturn;

		FORAPythonUtil::deserializer(toReturn, inData);

		*inObj = *toReturn;
		}

	static PolymorphicSharedPtr<SerializedObject> 
					deserializeEntireObjectGraphFromString(std::string dataStr)
		{
		return SerializedObjectInflater::inflateOnce(
			PolymorphicSharedPtr<NoncontiguousByteBlock>(
				new NoncontiguousByteBlock(std::move(dataStr))
				)
			);
		}

	static std::string SerializedObjectToString(PolymorphicSharedPtr<SerializedObject>& inObject)
		{
		return inObject->toString();
		}

	static uword_t SerializedObjectSize(PolymorphicSharedPtr<SerializedObject>& in)
		{
		return in->getSerializedData()->totalByteCount();
		}

	static std::string serializeEntireObjectGraphToString(PolymorphicSharedPtr<SerializedObject>& o)
		{
		ScopedPyThreads releaseTheGil;

		return SerializedObjectFlattener::flattenOnce(o)->toString();
		}

	static PolymorphicSharedPtr<SerializedObject> encodeStringInSerializedObject(std::string s)
		{
		return SerializedObject::serialize(s, PolymorphicSharedPtr<VectorDataMemoryManager>());
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;
		
		class_<PolymorphicSharedPtr<SerializedObject> >(
					"SerializedObject",
					no_init
					)
			.def("__init__", make_constructor(PolymorphicSharedPtr<SerializedObject>::Constructor0))
			.def("__cmp__", SerializedObjectCmp)
			.def("__hash__", SerializedObjectPyHash)
			.add_property("hash", SerializedObjectHash)
			.def("__getstate__", SerializedObjectSerializer)
			.def("__setstate__", SerializedObjectDeserializer)
			.def("serializeEntireObjectGraphToString", serializeEntireObjectGraphToString)
			.def("__str__", SerializedObjectToString)
			.def("__len__", SerializedObjectSize)
			.enable_pickling()
			;
		
		def("deserializeEntireObjectGraphFromString", &deserializeEntireObjectGraphFromString);
		def("encodeStringInSerializedObject", &encodeStringInSerializedObject);
		}
	
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<SerializedObjectWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<
	SerializedObjectWrapper>::registerWrapper();

