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

import pyfora.PyObjectNodes as PyObjectNodes
import pyfora.PureImplementationMapping as PureImplementationMapping

import numpy as np


class PurePythonNumpyArray:
    def __init__(self, data, dtype, shape):
        self.data = data
        self.dtype = dtype
        self.shape = shape

    def __len__(self):
        return len(self.data)

    def __getitem__(self, ix):
        return self.data[ix]

class PurePythonNumpyArrayMapping(PureImplementationMapping.PureImplementationMapping):
    def getMappablePythonTypes(self):
        return [np.ndarray]

    def getMappableInstances(self):
        return []
        
    def getPurePythonTypes(self):
        return [PurePythonNumpyArray]

    def mapPythonInstanceToPyforaInstance(self, numpyArray):
        return PurePythonNumpyArray(
            numpyArray.tostring(), 
            numpyArray.dtype.str,
            numpyArray.shape
            )

    def mapPyforaInstanceToPythonInstance(self, pureNumpyArray):
        """Given the converted members of the pyfora object as a dict, return an instance of the mappable type."""
        array = np.fromstring(pureNumpyArray.data, pureNumpyArray.dtype)
        array.shape = pureNumpyArray.shape
        return array


