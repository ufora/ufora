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
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator
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

def roundtripConvert(toConvert, vdm, verbose=False):
    t0 = time.time()

    mappings = PureImplementationMappings.PureImplementationMappings()
    registry = ObjectRegistry.ObjectRegistry(stringEncoder=lambda s:s)

    walker = PyObjectWalker.PyObjectWalker(
        purePythonClassMapping=mappings,
        objectRegistry=registry
        )

    objId = walker.walkPyObject(toConvert)

    if verbose:
        for k,v in registry.objectIdToObjectDefinition.iteritems():
            print k, repr(v)[:150]

    t1 = time.time()

    objId, registry.objectIdToObjectDefinition = pickle.loads(pickle.dumps((objId,registry.objectIdToObjectDefinition),2))

    t2 = time.time()

    path = os.path.join(os.path.abspath(os.path.split(pyfora.__file__)[0]), "fora")
    moduleTree = ModuleDirectoryStructure.ModuleDirectoryStructure.read(path, "purePython", "fora")
    converter = Converter.constructConverter(moduleTree.toJson(), vdm,stringDecoder=lambda s:s)
    anObjAsImplval = converter.convertDirectly(objId, registry)

    t3 = time.time()

    transformer = PyforaToJsonTransformer.PyforaToJsonTransformer(stringEncoder=lambda s:s)

    anObjAsJson = converter.transformPyforaImplval(
        anObjAsImplval,
        transformer,
        PyforaToJsonTransformer.ExtractVectorContents(vdm)
        )

    t4 = time.time()

    rehydrator = PythonObjectRehydrator.PythonObjectRehydrator(
        mappings, 
        allowUserCodeModuleLevelLookups=False,
        stringDecoder=lambda s:s
        )

    finalResult = rehydrator.convertJsonResultToPythonObject(anObjAsJson)

    t5 = time.time()

    return finalResult, {'0: walking': t1-t0, '1: serialize/deserialize': t2 - t1, '2: toImplval': t3-t2, '3: toJson': t4-t3, '4: toPython': t5-t4}


class ConverterTest(unittest.TestCase):
    def test_walking_unconvertible_module(self):
        mappings = PureImplementationMappings.PureImplementationMappings()
        registry = ObjectRegistry.ObjectRegistry()

        walker = PyObjectWalker.PyObjectWalker(
            purePythonClassMapping=mappings,
            objectRegistry=registry
            )

        objId = walker.walkPyObject(ThisFunctionIsImpure)

        self.assertEqual(sorted(registry.objectIdToObjectDefinition[objId].freeVariableMemberAccessChainsToId.keys()), ["multiprocessing"])

    
    def test_conversion_metadata(self):
        for anInstance in [ThisIsAClass(), ThisIsAFunction]:
            mappings = PureImplementationMappings.PureImplementationMappings()
            registry = ObjectRegistry.ObjectRegistry()

            walker = PyObjectWalker.PyObjectWalker(
                purePythonClassMapping=mappings,
                objectRegistry=registry
                )

            objId = walker.walkPyObject(anInstance)

            path = os.path.join(os.path.abspath(os.path.split(pyfora.__file__)[0]), "fora")
            moduleTree = ModuleDirectoryStructure.ModuleDirectoryStructure.read(path, "purePython", "fora")
            converter = Converter.constructConverter(moduleTree.toJson(), None)
            anObjAsImplval = converter.convertDirectly(objId, registry)

            transformer = PyforaToJsonTransformer.PyforaToJsonTransformer()

            anObjAsJson = converter.transformPyforaImplval(
                anObjAsImplval,
                transformer,
                PyforaToJsonTransformer.ExtractVectorContents(None)
                )

            rehydrator = PythonObjectRehydrator.PythonObjectRehydrator(mappings, allowUserCodeModuleLevelLookups=False)

            convertedInstance = rehydrator.convertJsonResultToPythonObject(anObjAsJson)

            def walkJsonObject(o):
                if isinstance(o, str):
                    try:
                        o_decoded = base64.b64decode(o)
                        return base64.b64encode(o_decoded.replace("100", "200"))
                    except:
                        return o
                if isinstance(o, dict):
                    return {k:walkJsonObject(o[k]) for k in o}
                if isinstance(o, tuple):
                    return tuple([walkJsonObject(x) for x in o])
                return o

            convertedInstanceModified = rehydrator.convertJsonResultToPythonObject(walkJsonObject(anObjAsJson))

            if anInstance is ThisIsAFunction:
                self.assertEqual(anInstance(), 100)
                self.assertEqual(convertedInstance(), 100)
                self.assertEqual(convertedInstanceModified(), 200)
            else:
                self.assertEqual(anInstance.f(), 100)
                self.assertEqual(convertedInstance.f(), 100)
                self.assertEqual(convertedInstanceModified.f(), 200)


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
        vdm = FORANative.VectorDataManager(CallbackScheduler.singletonForTesting(), 10000000)

        t0 = time.time()
        aNewArray,timings = roundtripConvert(toCheck, vdm)

        for k in sorted(timings):
            print k, timings[k]
