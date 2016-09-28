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
import os
import base64
import numpy
import multiprocessing
import cPickle as pickle
import time

import ufora.FORA.python.ModuleDirectoryStructure as ModuleDirectoryStructure
import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PureImplementationMapping as PureImplementationMapping
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.ObjectRegistry as ObjectRegistry
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
import pyfora.BinaryObjectRegistryDeserializer as BinaryObjectRegistryDeserializer
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator
import pyfora.TypeDescription as TypeDescription
import pyfora
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

def roundtripConvert(toConvert, vdm, allowUserCodeModuleLevelLookups = False, verbose=False):
    t0 = time.time()

    mappings = PureImplementationMappings.PureImplementationMappings()
    binaryObjectRegistry = BinaryObjectRegistry.BinaryObjectRegistry()

    walker = PyObjectWalker.PyObjectWalker(
        purePythonClassMapping=mappings,
        objectRegistry=binaryObjectRegistry
        )

    objId = walker.walkPyObject(toConvert)

    binaryObjectRegistry.defineEndOfStream()

    registry = ObjectRegistry.ObjectRegistry()
    BinaryObjectRegistryDeserializer.deserializeFromString(binaryObjectRegistry.str(), registry, lambda x:x)

    t1 = time.time()

    objId, registry.objectIdToObjectDefinition = pickle.loads(pickle.dumps((objId,registry.objectIdToObjectDefinition),2))

    t2 = time.time()

    converter = Converter.constructConverter(Converter.canonicalPurePythonModule(), vdm)
    anObjAsImplval = converter.convertDirectly(objId, registry)

    t3 = time.time()

    outputStream = BinaryObjectRegistry.BinaryObjectRegistry()

    root_id, needsLoad = converter.transformPyforaImplval(
        anObjAsImplval,
        outputStream,
        PyforaToJsonTransformer.ExtractVectorContents(vdm)
        )

    needsLoad = False
    result = {'data': outputStream.str(), 'root_id': root_id}

    t4 = time.time()

    rehydrator = PythonObjectRehydrator.PythonObjectRehydrator(
        mappings, 
        allowUserCodeModuleLevelLookups=allowUserCodeModuleLevelLookups
        )

    finalResult = rehydrator.convertEncodedStringToPythonObject(outputStream.str(), root_id)

    t5 = time.time()

    return finalResult, {'0: walking': t1-t0, '1: serialize/deserialize': t2 - t1, '2: toImplval': t3-t2, '3: toJson': t4-t3, '4: toPython': t5-t4}


class ConverterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Converter.canonicalPurePythonModule()

    def test_walking_unconvertible_module(self):
        mappings = PureImplementationMappings.PureImplementationMappings()
        registry = ObjectRegistry.ObjectRegistry()

        walker = PyObjectWalker.PyObjectWalker(
            purePythonClassMapping=mappings,
            objectRegistry=registry
            )

        objId = walker.walkPyObject(ThisFunctionIsImpure)

        self.assertEqual(sorted(registry.objectIdToObjectDefinition[objId].freeVariableMemberAccessChainsToId.keys()), ["multiprocessing"])

    def test_roundtrip_conversion_simple(self):
        vdm = FORANative.VectorDataManager(CallbackScheduler.singletonForTesting(), 10000000)

        for obj in [10, 10.0, "asdf", None, False, True, 
                [], (), [1,2], [1, [1]], (1,2), (1,2,[]), {1:2}
                ]:
            self.assertEqual(roundtripConvert(obj, vdm)[0], obj, obj)

    def test_roundtrip_convert_function(self):
        vdm = FORANative.VectorDataManager(CallbackScheduler.singletonForTesting(), 10000000)

        self.assertTrue(
            roundtripConvert(ThisIsAFunction, vdm, allowUserCodeModuleLevelLookups=True)[0] 
                is ThisIsAFunction
            )
        self.assertTrue(
            roundtripConvert(ThisIsAClass, vdm, allowUserCodeModuleLevelLookups=True)[0] 
                is ThisIsAClass
            )
        self.assertTrue(
            isinstance(
                roundtripConvert(ThisIsAClass(), vdm, allowUserCodeModuleLevelLookups=True)[0],
                ThisIsAClass
                )
            )

    def test_conversion_metadata(self):
        for anInstance in [ThisIsAClass(), ThisIsAFunction]:
            mappings = PureImplementationMappings.PureImplementationMappings()
            registry = ObjectRegistry.ObjectRegistry()

            walker = PyObjectWalker.PyObjectWalker(
                purePythonClassMapping=mappings,
                objectRegistry=registry
                )

            objId = walker.walkPyObject(anInstance)

            converter = Converter.constructConverter(Converter.canonicalPurePythonModule(), None)
            anObjAsImplval = converter.convertDirectly(objId, registry)

            stream = BinaryObjectRegistry.BinaryObjectRegistry()

            root_id, needsLoading = converter.transformPyforaImplval(
                anObjAsImplval,
                stream,
                PyforaToJsonTransformer.ExtractVectorContents(None)
                )
            assert not needsLoading

            rehydrator = PythonObjectRehydrator.PythonObjectRehydrator(mappings, allowUserCodeModuleLevelLookups=False)

            convertedInstance = rehydrator.convertEncodedStringToPythonObject(stream.str(), root_id)

            convertedInstanceModified = rehydrator.convertEncodedStringToPythonObject(stream.str().replace("return 100", "return 200"), root_id)

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
            dt2 = TypeDescription.primitiveToDtype(TypeDescription.dtypeToPrimitive(array.dtype))
            self.assertEqual(str(dt.descr), str(dt2.descr))

    @PerformanceTestReporter.PerfTest("pyfora.ConvertionSpeed.strings_100k")
    def test_conversion_performance_strings(self):
        anArray = [str(ix) for ix in xrange(100000)]
        self.conversionTest(anArray)

    @PerformanceTestReporter.PerfTest("pyfora.ConvertionSpeed.ints_100k")
    def test_conversion_performance_ints(self):
        anArray = [ix for ix in xrange(100000)]
        self.conversionTest(anArray)

    @PerformanceTestReporter.PerfTest("pyfora.ConvertionSpeed.numpy_array_10mm")
    def test_conversion_performance_numpy(self):
        anArray = numpy.zeros(10000000)
        self.conversionTest(anArray)

    def conversionTest(self, toCheck):
        try:
            vdm = FORANative.VectorDataManager(CallbackScheduler.singletonForTesting(), 10000000)

            t0 = time.time()
            aNewArray,timings = roundtripConvert(toCheck, vdm)

            for k in sorted(timings):
                print k, timings[k]
        except:
            import traceback
            traceback.print_exc()
            self.assertTrue(False)

