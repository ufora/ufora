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
#ifndef core_python_ExposeAsClass_hpp
#define core_python_ExposeAsClass_hpp


#include <boost/python.hpp>
#include <string>

namespace Ufora {
namespace python {

template<class T>
class ExposeAsClass {
public:
		const static bool value = boost::is_class<T>::value;
};
template<>
class ExposeAsClass<std::string> {
public:
		const static bool value = false;
};

}
}

#endif

