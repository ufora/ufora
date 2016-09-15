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

import base64
import cPickle

class HaltTransformationException(Exception):
    """Exception to be raised if we wish to halt transformation for any reason."""

class ExtractVectorContents:
    def __init__(self, vdm):
        self.vdm = vdm
        self.vectorsNeedingLoad = []

    def __call__(self, vectorIVC):
        vdm = self.vdm
        
        if len(vectorIVC) == 0:
            return {'listContents': []}

        #if this is an unpaged vector we can handle it without callback
        if vdm.vectorDataIsLoaded(vectorIVC, 0, len(vectorIVC)):
            #see if it's a string. This is the only way to be holding a Vector of char
            if vectorIVC.isVectorOfChar():
                res = vdm.extractVectorContentsAsNumpyArray(vectorIVC, 0, len(vectorIVC))
                assert res is not None
                return {'string': res.tostring()}

            #see if it's simple enough to transmit as numpy data
            if len(vectorIVC.getVectorElementsJOR()) == 1 and len(vectorIVC) > 1:
                res = vdm.extractVectorContentsAsNumpyArray(vectorIVC, 0, len(vectorIVC))

                if res is not None:
                    assert len(res) == len(vectorIVC)
                    firstElement = vdm.extractVectorItem(vectorIVC, 0)
                    return {'contentsAsNumpyArray': res}

            #see if we can extract the data as a regular pythonlist
            res = vdm.extractVectorContentsAsPythonArray(vectorIVC, 0, len(vectorIVC)) 
            assert res is not None
            return {'listContents': res}

        self.vectorsNeedingLoad.append(vectorIVC)

        return res


