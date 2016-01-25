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
#include "SerializedObjectFlattener.hpp"

#include <stdint.h>
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/utilities.hpp"
#include "../../core/threading/ScopedThreadLocalContext.hpp"
#include "../../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"

using namespace Ufora::python;


class SerializedObjectFlattenerWrapper :
	public native::module::Exporter<SerializedObjectFlattenerWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "FORA";
		}
	
	void	dependencies(std::vector<std::string>& outTypes)
		{
		outTypes.push_back(typeid(PolymorphicSharedPtr<SerializedObject>).name());
		}
		
	static PolymorphicSharedPtr<NoncontiguousByteBlock> 
	flatten(PolymorphicSharedPtr<SerializedObjectFlattener>& flattener,
			PolymorphicSharedPtr<SerializedObject>& spo
			)
		{
		ScopedPyThreads threads;

		return flattener->flatten(spo);
		}
	
	static PolymorphicSharedPtr<SerializedObject> 
	inflate(PolymorphicSharedPtr<SerializedObjectInflater>& inflater,
			const PolymorphicSharedPtr<NoncontiguousByteBlock>& flattenedData
			)
		{
		ScopedPyThreads threads;

		return PolymorphicSharedPtr<SerializedObject>(
			inflater->inflate(flattenedData)
			);
		}
	
	static PolymorphicSharedPtr<NoncontiguousByteBlock>
	flattenPythonObjectUsingPickler(	
							PolymorphicSharedPtr<SerializedObjectFlattener>& flattener, 
							boost::python::object inObj,
							boost::python::object inPickleFunction,
							boost::python::object inPickleStreamExtractFunction,
							PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM
							)
		{
		typedef PolymorphicSharedPtr<SerializedObjectContext>  context_ptr;

		context_ptr context(new SerializedObjectContext(inVDMM));

		Ufora::threading::ScopedThreadLocalContext<context_ptr> contextSetter(context);
		
		inPickleFunction(inObj);

		boost::python::object res = inPickleStreamExtractFunction();

		std::string dataStr = boost::python::extract<std::string>(res)();

		PolymorphicSharedPtr<SerializedObject> serializedObj(
			new SerializedObject(
				PolymorphicSharedPtr<NoncontiguousByteBlock>(
					new NoncontiguousByteBlock(std::move(dataStr))
					),
				context
				)
			);
		
		
			{
			ScopedPyThreads threads;
			
			return flattener->flatten(serializedObj);
			}
		}
	
	static boost::python::object 
	inflatePythonObjectUsingPickler(	
					PolymorphicSharedPtr<SerializedObjectInflater>& inflater,
					boost::python::object pushBytesFunction,
					boost::python::object loadFunction,
					PolymorphicSharedPtr<NoncontiguousByteBlock> inStr,
					PolymorphicSharedPtr<VectorDataMemoryManager> inVDMM
					)
		{
		typedef PolymorphicSharedPtr<SerializedObjectContext>  context_ptr;

		PolymorphicSharedPtr<SerializedObject> serializedObj;

			{
			ScopedPyThreads threads;
			
			serializedObj = inflater->inflate(inStr);
			}

		context_ptr context(new SerializedObjectContext(inVDMM, serializedObj));

		Ufora::threading::ScopedThreadLocalContext<context_ptr> contextSetter(context);
		
		pushBytesFunction(serializedObj->getSerializedData()->toString());

		return loadFunction();
		}

	static uword_t getMemoizedSize(PolymorphicSharedPtr<SerializedObjectFlattener>& inFlattener)
		{
		return inFlattener->getMemoizedSize();
		}
	
	void exportPythonWrapper()
		{
		using namespace boost::python;
		
		class_<PolymorphicSharedPtr<SerializedObjectFlattener> >
				("SerializedObjectFlattener", no_init)
			.def("__init__", make_constructor(PolymorphicSharedPtr<SerializedObjectFlattener>::Constructor0))
			.def("flatten", &flatten)
			.def("getMemoizedSize", &getMemoizedSize)
			.def("flattenPythonObjectUsingPickler", &flattenPythonObjectUsingPickler)
			;
		
		class_<PolymorphicSharedPtr<SerializedObjectInflater> >
				("SerializedObjectInflater", no_init)
			.def("__init__", make_constructor(PolymorphicSharedPtr<SerializedObjectInflater>::Constructor0))
			.def("inflate", &inflate)
			.def("inflatePythonObjectUsingPickler", &inflatePythonObjectUsingPickler)
			;
		}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char 
native::module::Exporter<SerializedObjectFlattenerWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<SerializedObjectFlattenerWrapper>::registerWrapper();

