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

import numpy
import time
import unittest

import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
from pyfora.PythonObjectRehydrator import PythonObjectRehydrator
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.PurePython.Converter as Converter
import ufora.FORA.python.PurePython.PythonBinaryStreamToImplval as PythonBinaryStreamToImplval
import ufora.FORA.python.PurePython.PythonBinaryStreamFromImplval as PythonBinaryStreamFromImplval
import ufora.native.FORA as ForaNative
import ufora.native.CallbackScheduler as CallbackScheduler


class RoundTripPyforaConversionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vdm = ForaNative.VectorDataManager(
            CallbackScheduler.singletonForTesting(), 10000000)

    @classmethod
    def tearDownClass(cls):
        if cls.vdm is not None:
            cls.vdm.teardown()
            cls.vdm = None

    def roundtripConvert(self, pyObject, testName):
        try:
            _, timings = self._roundtripConvert(pyObject)

            for k in sorted(timings):
                print k, timings[k]
                PerformanceTestReporter.recordTest(
                    testName=testName+"."+k,
                    elapsedTime=timings[k],
                    metadata=None
                    )
                
        except:
            import traceback
            traceback.print_exc()
            self.assertTrue(False)

    def _roundtripConvert(self, pyObject):
        t0 = time.time()

        mappings = PureImplementationMappings.PureImplementationMappings()
        binaryObjectRegistry = BinaryObjectRegistry.BinaryObjectRegistry()

        walker = PyObjectWalker.PyObjectWalker(
            mappings,
            binaryObjectRegistry
            )

        root_id = walker.walkPyObject(pyObject)
        binaryObjectRegistry.defineEndOfStream()

        t1 = time.time()

        data = binaryObjectRegistry.str()

        streamReader = PythonBinaryStreamToImplval.constructConverter(
            Converter.canonicalPurePythonModule(), self.vdm)

        streamReader.read(data)
        anObjAsImplval = streamReader.getObjectById(root_id)
    
        t2 = time.time()

        converter = PythonBinaryStreamFromImplval.constructConverter(
            Converter.canonicalPurePythonModule(), self.vdm)

        root_id, data = converter.write(anObjAsImplval)

        t3 = time.time()

        rehydrator = PythonObjectRehydrator(
            mappings, allowUserCodeModuleLevelLookups=False)

        converted = rehydrator.convertEncodedStringToPythonObject(data, root_id)
        
        t4 = time.time()

        timings = {'py_to_binary': t1 - t0,
                   'binary_to_implVal': t2 - t1,
                   'implval_to_binary': t3 - t2,
                   'binary_to_python': t4 - t3}

        return converted, timings
        
    def test_conversion_performance_small_strings_100k(self):
        anArray = [str(ix) for ix in xrange(100000)]
        self.roundtripConvert(
            anArray,
            "pyfora.RoundTripConversion.small_strings_100k")

    def test_conversion_performance_ints_100k(self):
        anArray = [ix for ix in xrange(100000)]
        self.roundtripConvert(
            anArray,
            "pyfora.RoundTripConversion.ints_100k")

    def test_conversion_performance_mixed_ints_and_floats_100k(self):
        def elt(ix):
            if ix % 2:
                return float(ix)
            return ix
        anArray = [elt(ix) for ix in xrange(100000)]
        self.roundtripConvert(
            anArray,
            "pyfora.RoundTripConversion.mixed_ints_floats_100k")

    def test_conversion_performance_floats_100k(self):
        anArray = [float(ix) for ix in xrange(100000)]
        self.roundtripConvert(
            anArray,
            "pyfora.RoundTripConversion.floats_100k")
        
    def test_conversion_performance_numpy_10mm(self):
        anArray = numpy.zeros(10000000)
        self.roundtripConvert(
            anArray,
            "pyfora.RoundTripConversion.numpy_array_10mm")

    def test_conversion_performance_homogeneous_class_instances_10k(self):
        class C(object):
            def __init__(self, x):
                self.x = x
            def foo(self, y):
                return self.x + y

        classes = [C(ix) for ix in xrange(10000)]
        self.roundtripConvert(
            classes,
            "pyfora.RoundTripConversion.homogeneous_class_instances_10k")

    def test_conversion_performance_tuples_10k(self):
        tups = [tuple(range(ix % 10)) for ix in xrange(10000)]
        self.roundtripConvert(
            tups,
            "pyfora.RoundTripConversion.tuples_10k"
            )

    def test_conversion_performance_small_lists(self):
        small_lists = [range(ix % 10) for ix in xrange(10000)]
        self.roundtripConvert(
            small_lists,
            "pyfora.RoundTripConversion.small_lists_10k")

    def test_conversion_performance_heterogeneous_class_instances_10k(self):
        class C1(object):
            def __init__(self, x):
                self.x = x
            def foo(self, y):
                return self.x + y

        class C2(object):
            def __init__(self, x):
                self.y = x + 2
            def bar(self, arg0, arg1):
                return self.y * arg0 + arg1

        def elt(ix):
            if ix % 2:
                return C1(ix)
            return C2(ix)

        classes = [elt(ix) for ix in xrange(10000)]
        self.roundtripConvert(
            classes,
            "pyfora.RoundTripConversion.heterogeneous_class_instances_10k")

    def test_conversion_performance_functions_10k(self):
        def func(ix):
            def f(arg):
                return arg + ix
            return f

        funcs = [func(ix) for ix in xrange(10000)]
        self.roundtripConvert(
            funcs,
            "pyfora.RoundTripConversion.functions_10k")
        
        
    def test_conversion_performance_class_objects_10k(self):
        def class_factory(ix):
            class C(object):
                def __init__(self, x):
                    self.x = x
                def foo(self, arg):
                    return self.x + arg + ix
            return C

        classes = [class_factory(ix) for ix in xrange(10000)]
        self.roundtripConvert(
            classes,
            "pyfora.RoundTripConversion.class_objects_10k")

    
