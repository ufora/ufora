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

ASSUMED_OBJECT_BYTECOUNT_OVERHEAD = 20

class PyforaToJsonTransformer(object):
    def __init__(self, maxBytecount = None):
        self.anyListsThatNeedLoading = False
        self.bytesEncoded = 0
        self.maxBytecount = maxBytecount

    def transformListThatNeedsLoading(self, length):
        self.accumulateObjects(length)

        self.anyListsThatNeedLoading = True
        return {}

    def transformStringThatNeedsLoading(self, length):
        self.accumulateObjects(1, length)
        self.anyListsThatNeedLoading = True

        return {}

    def transformPrimitive(self, primitive):
        if isinstance(primitive, str):
            primitive = base64.b64encode(primitive).encode("utf8")

        self.accumulateObjects(1, len(primitive) if isinstance(primitive, str) else 0)        
        return {'primitive': primitive}

    def transformTuple(self, tupleMembers):
        self.accumulateObjects(1)
        return {'tuple': tupleMembers}

    def transformList(self, listMembers):
        self.accumulateObjects(1)
        return {'list': listMembers}

    def transformHomogenousList(self, firstElement, allElementsAsNumpyArrays):
        numpyAsStrings = [{'data':base64.b64encode(x.tostring()).encode("utf8"), 'length':len(x)} for x in allElementsAsNumpyArrays]
        numpyDtypeAsString = base64.b64encode(cPickle.dumps(allElementsAsNumpyArrays[0].dtype))

        self.accumulateObjects(1, sum(len(x) for x in numpyAsStrings) + len(numpyDtypeAsString))

        return {
            'homogenousListNumpyDataStringsAndSizes': numpyAsStrings,
            'dtype': numpyDtypeAsString,
            'firstElement': firstElement,
            'length': sum(len(x) for x in allElementsAsNumpyArrays)
            }

    def transformDict(self, keys, values):
        self.accumulateObjects(1)
        return {
            'dict': {
                'keys': keys,
                'values': values
                }
            }

    def transformSingleton(self, singletonName):
        self.accumulateObjects(1)
        return {'singleton': singletonName}

    def transformBuiltinException(self, builtinExceptionTypeName, argsTuple):
        self.accumulateObjects(1)
        return {
            'builtinException': builtinExceptionTypeName,
            'args': argsTuple
            }

    def transformPyAbortException(self, pyAbortExceptionTypeName, argsTuple):
        self.accumulateObjects(1)
        return {
            'pyAbortException': pyAbortExceptionTypeName,
            'args': argsTuple
            }

    def transformInvalidPythonOperationException(self, operationText):
        self.accumulateObjects(1)
        return {'InvalidPyforaOperation': operationText}

    def transformBoundMethod(self, instance, name):
        self.accumulateObjects(1)
        return {'boundMethodOn': instance, 'methodName': name}

    def transformClassInstance(self, classObject, members):
        self.accumulateObjects(1)
        return {'classInstance': classObject, 'members': members}

    def transformClassObject(self, filename, linenumber, members, file_text_id):
        self.accumulateObjects(1)
        return {'classObject': (filename, linenumber), 'members': members, 'file_text': file_text_id }

    def transformFunctionInstance(self, filename, linenumber, members, file_text_id):
        self.accumulateObjects(1)
        return {'functionInstance': (filename, linenumber), 'members': members, 'file_text': file_text_id}

    def transformModuleLevelObject(self, object_path):
        self.accumulateObjects(1)
        return {'moduleLevelObject': object_path}

    def accumulateObjects(self, objectCount, extraBytes=0):
        self.bytesEncoded += objectCount * ASSUMED_OBJECT_BYTECOUNT_OVERHEAD + extraBytes
        self._checkIfThresholdExceeded()

    def _checkIfThresholdExceeded(self):
        if self.maxBytecount is not None and self.bytesEncoded > self.maxBytecount:
            raise HaltTransformationException()

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
                    return {'firstElement': firstElement, 'contentsAsNumpyArrays': [res]}

            #see if we can extract the data as a regular pythonlist
            res = vdm.extractVectorContentsAsPythonArray(vectorIVC, 0, len(vectorIVC)) 
            assert res is not None
            return {'listContents': res}

        self.vectorsNeedingLoad.append(vectorIVC)

        return res


