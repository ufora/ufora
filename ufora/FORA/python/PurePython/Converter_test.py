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
import numpy
import multiprocessing
import cPickle as pickle
import time

import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.ObjectRegistry as ObjectRegistry
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
import pyfora.BinaryObjectRegistryDeserializer as BinaryObjectRegistryDeserializer
from pyfora.PythonObjectRehydrator import PythonObjectRehydrator
import pyfora.TypeDescription as TypeDescription
import ufora.FORA.python.PurePython.Converter as Converter
import ufora.FORA.python.PurePython.PyforaToJsonTransformer as PyforaToJsonTransformer
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.native.FORA as FORANative
import ufora.native.CallbackScheduler as CallbackScheduler


class ThisIsAClass:
    def f(self):
    	return 100


def ThisIsAFunction():
    return 100


def ThisFunctionIsImpure():
    return multiprocessing.cpu_count()


def roundtripConvert(toConvert, vdm, allowUserCodeModuleLevelLookups = False):
    t0 = time.time()

    mappings = PureImplementationMappings.PureImplementationMappings()
    binaryObjectRegistry = BinaryObjectRegistry.BinaryObjectRegistry()

    walker = PyObjectWalker.PyObjectWalker(
        mappings,
        binaryObjectRegistry
        )

    objId = walker.walkPyObject(toConvert)

    binaryObjectRegistry.defineEndOfStream()

    t1 = time.time()

    registry = ObjectRegistry.ObjectRegistry()

    BinaryObjectRegistryDeserializer.deserializeFromString(
        binaryObjectRegistry.str(), registry, lambda x:x)

    t2 = time.time()

    objId, registry.objectIdToObjectDefinition = pickle.loads(
        pickle.dumps((objId,registry.objectIdToObjectDefinition),2))

    t3 = time.time()

    converter = Converter.constructConverter(
        Converter.canonicalPurePythonModule(), vdm)
    anObjAsImplval = converter.convertDirectly(objId, registry)

    t4 = time.time()

    outputStream = BinaryObjectRegistry.BinaryObjectRegistry()

    root_id, needsLoad = converter.transformPyforaImplval(
        anObjAsImplval,
        outputStream,
        PyforaToJsonTransformer.ExtractVectorContents(vdm)
        )

    needsLoad = False

    t5 = time.time()

    rehydrator = PythonObjectRehydrator(
        mappings, 
        allowUserCodeModuleLevelLookups
        )

    finalResult = rehydrator.convertEncodedStringToPythonObject(
        outputStream.str(), root_id)

    t6 = time.time()

    return finalResult, {'0: walking': t1 - t0,
                         '1: deserializeFromString': t2 - t1,
                         '2: toImplval': t4 - t3,
                         '3: serialze implVal': t5 - t4,
                         '4: toPython': t6 - t5}


class ConverterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Converter.canonicalPurePythonModule()

    def test_walking_unconvertible_module(self):
        mappings = PureImplementationMappings.PureImplementationMappings()
        binaryObjectRegistry = BinaryObjectRegistry.BinaryObjectRegistry()

        walker = PyObjectWalker.PyObjectWalker(
            mappings,
            binaryObjectRegistry
            )

        objId = walker.walkPyObject(ThisFunctionIsImpure)
        binaryObjectRegistry.defineEndOfStream()

        registry = ObjectRegistry.ObjectRegistry()
        BinaryObjectRegistryDeserializer.deserializeFromString(
            binaryObjectRegistry.str(), registry, lambda x:x)

        self.assertEqual(
            sorted(
                registry.objectIdToObjectDefinition[objId]\
                .freeVariableMemberAccessChainsToId.keys()
                ),
            ["multiprocessing"]
            )

    def test_roundtrip_conversion_simple(self):
        vdm = FORANative.VectorDataManager(
            CallbackScheduler.singletonForTesting(), 10000000)

        for obj in [10, 10.0, "asdf", None, False, True, 
                [], (), [1,2], [1, [1]], (1,2), (1,2,[]), {1:2}
                ]:
            self.assertEqual(roundtripConvert(obj, vdm)[0], obj, obj)

    def test_roundtrip_convert_function(self):
        vdm = FORANative.VectorDataManager(
            CallbackScheduler.singletonForTesting(), 10000000)

        self.assertTrue(
            roundtripConvert(ThisIsAFunction,
                             vdm, 
                             allowUserCodeModuleLevelLookups=True
                         )[0] 
                is ThisIsAFunction
            )
        self.assertTrue(
            roundtripConvert(ThisIsAClass,
                             vdm,
                             allowUserCodeModuleLevelLookups=True
                         )[0] 
                is ThisIsAClass
            )
        self.assertTrue(
            isinstance(
                roundtripConvert(ThisIsAClass(),
                                 vdm,
                                 allowUserCodeModuleLevelLookups=True
                             )[0],
                ThisIsAClass
                )
            )

    def test_conversion_metadata(self):
        for anInstance in [ThisIsAClass(), ThisIsAFunction]:
            mappings = PureImplementationMappings.PureImplementationMappings()

            binaryObjectRegistry = BinaryObjectRegistry.BinaryObjectRegistry()

            walker = PyObjectWalker.PyObjectWalker(
                mappings,
                binaryObjectRegistry
                )

            objId = walker.walkPyObject(anInstance)
            binaryObjectRegistry.defineEndOfStream()

            converter = Converter.constructConverter(
                Converter.canonicalPurePythonModule(),
                None
                )

            registry = ObjectRegistry.ObjectRegistry()

            BinaryObjectRegistryDeserializer.deserializeFromString(
                binaryObjectRegistry.str(),
                registry,
                lambda x:x
                )

            anObjAsImplval = converter.convertDirectly(objId, registry)

            stream = BinaryObjectRegistry.BinaryObjectRegistry()

            root_id, needsLoading = converter.transformPyforaImplval(
                anObjAsImplval,
                stream,
                PyforaToJsonTransformer.ExtractVectorContents(None)
                )
            assert not needsLoading

            rehydrator = PythonObjectRehydrator(mappings, False)

            convertedInstance = rehydrator.convertEncodedStringToPythonObject(
                stream.str(), root_id)

            convertedInstanceModified = rehydrator.convertEncodedStringToPythonObject(
                stream.str().replace("return 100", "return 200"),
                root_id)

            if anInstance is ThisIsAFunction:
                self.assertEqual(anInstance(), 100)
                self.assertEqual(convertedInstance(), 100)
                self.assertEqual(convertedInstanceModified(), 200)
            else:
                self.assertEqual(anInstance.f(), 100)
                self.assertEqual(convertedInstance.f(), 100)
                self.assertEqual(convertedInstanceModified.f(), 200)

    def test_numpy_dtype_conversion(self):
        for array in [
                numpy.array([1.0,2.0]),
                numpy.zeros(2, dtype=[('f0','<f8'), ('f1','<f8')]),
                numpy.array([1]),
                numpy.array([False])
                ]:
            dt = array.dtype
            dt2 = TypeDescription.primitiveToDtype(
                TypeDescription.dtypeToPrimitive(array.dtype))
            self.assertEqual(str(dt.descr), str(dt2.descr))

