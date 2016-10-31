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
#include "Hash.hpp"
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../python/CPPMLWrapper.hpp"
#include "../python/ScopedPyThreads.hpp"
#include "../containers/ImmutableTreeVector.py.hpp"
#include "../containers/ImmutableTreeSet.py.hpp"


namespace Ufora {

class HashWrapper :
		public native::module::Exporter<HashWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "Hash";
			}
		void	getDefinedTypes(std::vector<std::string>& outTypes)
			{
			outTypes.push_back(typeid(Hash).name());
			}

		static Hash hashString(std::string s)
			{
			ScopedPyThreads threads;
			return Hash::CityHash(&s[0], s.size());
			}
		static int32_t hash(Hash& in)
			{
			return ((int32_t*)&in)[0];
			}
		static Hash add(Hash& h, Hash& r)
			{
			ScopedPyThreads threads;
			return h + r;
			}
		static Hash add2(Hash& h, std::string r)
			{
			ScopedPyThreads threads;
			return h + hashString(r);
			}
		static uint32_t hashGetItem(Hash& h, uint32_t ix)
			{
			if (ix < 5)
				return h[ix];
			return 0;
			}
		static Hash* CreateHash(uint32_t ix)
			{
			return new Hash(ix);
			}
		static int HashCMP(Hash& h, boost::python::object o)
			{
			boost::python::extract<Hash> otherHash(o);
			if (otherHash.check())
				return h.cmp(otherHash());
			return -1;
			}
		static Hash xorHash(Hash& h1, Hash& h2)
			{
			Hash out;
			for (long k = 0; k < 5;k++)
				out[k] = h1[k] ^ h2[k];
			return out;
			}

		template<class T>
		static std::string simpleSerializer(const T& in)
			{
			ScopedPyThreads threads;

			return ::serialize<T>(in);
			}

		template<class T>
		static void simpleDeserializer(T& out, std::string inByteBlock)
			{
			ScopedPyThreads threads;

			out = ::deserialize<T>(inByteBlock);
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			using namespace boost::python;
			class_<Hash >("Hash", init<>() )
				.def("__init__", make_constructor(CreateHash) )
				.def("__str__", &hashToString)
				.def("__add__", &add)
				.def("__add__", &add2)
				.def("xor", &xorHash)
				.def("sha1", &hashString)
				.staticmethod("sha1")
				.def("stringToHash", &stringToHash)
				.staticmethod("stringToHash")
				.def("__repr__", &hashToString)
				.def("__hash__", &hash)
				.def("__cmp__", &HashCMP)
				.def("__getitem__", &hashGetItem)
				.def("__getstate__", simpleSerializer<Hash>)
				.def("__setstate__", simpleDeserializer<Hash>)
				;

			PythonWrapper<ImmutableTreeSet<Hash> >::exportPythonInterface("Hash");
			PythonWrapper<ImmutableTreeVector<Hash> >::exportPythonInterface("Hash");
			}
};

}

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<
	Ufora::HashWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			Ufora::HashWrapper>::registerWrapper();

