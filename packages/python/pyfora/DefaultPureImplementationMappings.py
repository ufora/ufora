#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.BuiltinPureImplementationMappings as BuiltinPureImplementationMappings
import pyfora.typeConverters.Numpy as Numpy
import pyfora.typeConverters.Pandas as Pandas
import pyfora.typeConverters.Complex as Complex

defaultMapping_ = PureImplementationMappings.PureImplementationMappings()

for _ in BuiltinPureImplementationMappings.generateMappings():
    defaultMapping_.addMapping(_)

for _ in Numpy.generateMappings():
    defaultMapping_.addMapping(_)

for _ in Pandas.generateMappings():
    defaultMapping_.addMapping(_)

for _ in Complex.generateMappings():
    defaultMapping_.addMapping(_)

def getMappings():
    return defaultMapping_

def addMapping(mapping):
    """Register an instance of PureImplementationMapping with the default mapping model.

    This is the primary way that users can register mappings for libraries that are not part
    of the default pyfora mapping libraries.
    """
    defaultMapping_.addMapping(mapping)



