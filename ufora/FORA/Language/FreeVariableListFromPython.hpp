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

#include <stdint.h>
#include <boost/python.hpp>
#include "../Core/ImplValContainer.hppml"
#include "../../core/containers/ImmutableTreeMap.hppml"
#include "../../core/math/Nullable.hpp"

namespace Fora {

inline ImmutableTreeMap<Symbol, pair<ImplValContainer, Nullable<Symbol> > > 
						freeVariableListFromPython(boost::python::dict freeVariables)		
	{
	ImmutableTreeMap<Symbol, pair<ImplValContainer, Nullable<Symbol> > > result;

	boost::python::list items = freeVariables.items();

	for (long k = 0; k < boost::python::len(items); k++)
		try {
			std::string name = boost::python::extract<string>(items[k][0])();

			boost::python::object value  = items[k][1];

			if (boost::python::extract<ImplValContainer>(value).check())
				result = result + Symbol(name) + make_pair(
					boost::python::extract<ImplValContainer>(value)(),
					Nullable<Symbol>()
					);
			else
				{
				boost::python::object iv = value[0];
				boost::python::object symbol = value[1];

				lassert(boost::python::extract<ImplValContainer>(iv).check());

				if (symbol.ptr() == boost::python::object().ptr())
					result = result + Symbol(name) + make_pair(
						boost::python::extract<ImplValContainer>(iv)(),
						Nullable<Symbol>()
						);
				else
					result = result + Symbol(name) + make_pair(
						boost::python::extract<ImplValContainer>(iv)(),
						Nullable<Symbol>(
							Symbol(
								boost::python::extract<std::string>(symbol)()
								)
							)
						);
				}
			}
		catch(...) {
			throw std::logic_error(
				"Invalid freeVariable list. Arguments must be a dictionary of"
				" string to IVC, (IVC,String) or (IVC, None)"
				);
			}

	return result;
	}

}

