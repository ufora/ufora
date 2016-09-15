#   Copyright 2016 Ufora Inc.
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

import unittest
import ufora.native.FORA as ForaNative
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PyObjectWalker as PyObjectWalker
import ufora.FORA.python.PurePython.Converter as Converter
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.FORA.python.PurePython.PyforaToJsonTransformer as PyforaToJsonTransformer
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator

import pickle

def roundtripConvert(pyObject):
    vdm = ForaNative.VectorDataManager(CallbackScheduler.singletonForTesting(), 10000000)

    converter = Converter.constructConverter(Converter.canonicalPurePythonModule(), vdm)

    streamReader = ForaNative.PythonBinaryStreamToImplval(
        vdm,
        converter.nativeConstantConverter,
        converter.nativeListConverter
        )

    mappings = PureImplementationMappings.PureImplementationMappings()
    binaryObjectRegistry = BinaryObjectRegistry.BinaryObjectRegistry()

    walker = PyObjectWalker.PyObjectWalker(
        purePythonClassMapping=mappings,
        objectRegistry=binaryObjectRegistry
        )

    root_id = walker.walkPyObject(pyObject)
    binaryObjectRegistry.defineEndOfStream()

    data = binaryObjectRegistry.str()

    streamReader.read(data)
    
    stream = BinaryObjectRegistry.BinaryObjectRegistry()
    anObjAsImplval = streamReader.getObjectById(root_id)

    root_id, needsLoading = converter.transformPyforaImplval(
        anObjAsImplval,
        stream,
        PyforaToJsonTransformer.ExtractVectorContents(vdm)
        )
    assert not needsLoading

    rehydrator = PythonObjectRehydrator.PythonObjectRehydrator(mappings, allowUserCodeModuleLevelLookups=False)

    return rehydrator.convertJsonResultToPythonObject(stream.str(), root_id)




class PythonBinaryStreamToImplvalTest(unittest.TestCase):
    def test_deserialize_primitives(self):
        for value in [1,1.0,"1.0",None,False, [], [1.0], [1.0]]:
            self.assertEqual(value, roundtripConvert(value))
