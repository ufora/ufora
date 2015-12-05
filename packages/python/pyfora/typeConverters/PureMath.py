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

import pyfora.PureImplementationMapping as PureImplementationMapping


class LogFunction:
    def __call__(self, a):
        if not isinstance(a, float):
            a = float(a)
        
        return LogFunction.__pyfora_builtins__.logFunction(a)

def generateMappings():
    import math
    
    mappings_ = [(math.log, LogFunction)]

    tr = [PureImplementationMapping.InstanceMapping(instance, pureType) for \
          (instance, pureType) in mappings_]

    return tr


