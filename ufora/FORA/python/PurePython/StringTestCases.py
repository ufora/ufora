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

import time
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import sys

class StringTestCases(object):
    """Test cases for pyfora strings"""

    def test_string_indexing(self):
        def f():
            a = "abc"
            return (a[0], a[1], a[2], a[-1], a[-2])
        self.equivalentEvaluationTest(f)

    def test_strings_with_weird_characters(self):
        x = "\xb0"
        def f():
            return (x,"\xb0")
        self.equivalentEvaluationTest(f)

    def test_large_string_indexing_perf(self):
        def f(ct, passCt):
            x = "asdfasdf" * (ct / 8)
            res = 0
            for _ in xrange(passCt):
                for ix in xrange(len(x)):
                    res = res + len(x[ix])
            return res

        self.evaluateWithExecutor(f, 1000000, 1)
        self.evaluateWithExecutor(f, 10000, 1)
        
        @PerformanceTestReporter.PerfTest("pyfora.string_indexing.large_string")
        def test1():
            self.evaluateWithExecutor(f, 1000000, 100)
        
        @PerformanceTestReporter.PerfTest("pyfora.string_indexing.small_string")
        def test2():
            self.evaluateWithExecutor(f, 10000, 10000)
        
        test1()
        test2()

    def test_string_slicing(self):
        def f(ct, passCt,chars):
            x = "asdfasdf" * (ct / 8)
            res = 0
            for _ in xrange(passCt):
                for ix in xrange(len(x)):
                    res = res + len(x[ix:ix+chars])
            return res

        self.evaluateWithExecutor(f, 1000000, 1, 2)
        self.evaluateWithExecutor(f, 10000, 1, 2)
        
        def runTest(func, name):
            PerformanceTestReporter.PerfTest(name)(func)()

        runTest(lambda: self.evaluateWithExecutor(f, 1000000, 10, 2), "pyfora.string_slicing_10mm.2_char_large_string.pyfora")
        runTest(lambda: self.evaluateWithExecutor(f, 1000000, 10, 200), "pyfora.string_slicing_10mm.200_char_large_string.pyfora")
        runTest(lambda: self.evaluateWithExecutor(f, 10000, 1000, 2), "pyfora.string_slicing_10mm.2_char_small_string.pyfora")
        runTest(lambda: self.evaluateWithExecutor(f, 10000, 1000, 200), "pyfora.string_slicing_10mm.200_char_small_string.pyfora")
        
        sys.setcheckinterval(100000)

        runTest(lambda: f(1000000, 10, 2), "pyfora.string_slicing_10mm.2_char_large_string.native")
        runTest(lambda: f(1000000, 10, 200), "pyfora.string_slicing_10mm.200_char_large_string.native")
        runTest(lambda: f(10000, 1000, 2), "pyfora.string_slicing_10mm.2_char_small_string.native")
        runTest(lambda: f(10000, 1000, 200), "pyfora.string_slicing_10mm.200_char_small_string.native")
        
        sys.setcheckinterval(100)

    def test_string_slicing_into_vector(self):
        def testFunction(ct, passCt,chars):
            x = "asdfasdf" * (ct / 8)
            res = 0
            for _ in xrange(passCt):
                v = [x[ix*chars:ix*chars+chars] for ix in xrange(len(x) / chars)]
                for e in v:
                    res = res + len(e)
            return res
        f = testFunction

        self.evaluateWithExecutor(f, 1000000, 1, 2)
        self.evaluateWithExecutor(f, 10000, 1, 2)
        
        def runTest(func, name):
            PerformanceTestReporter.PerfTest(name)(func)()

        runTest(lambda: self.evaluateWithExecutor(f, 1000000, 10, 2), "pyfora.string_slicing_into_vector_10mm.2_char_large_string.pyfora")
        runTest(lambda: self.evaluateWithExecutor(f, 1000000, 1000, 200), "pyfora.string_slicing_into_vector_10mm.200_char_large_string.pyfora")
        runTest(lambda: self.evaluateWithExecutor(f, 10000, 1000, 2), "pyfora.string_slicing_into_vector_10mm.2_char_small_string.pyfora")
        runTest(lambda: self.evaluateWithExecutor(f, 10000, 100000, 200), "pyfora.string_slicing_into_vector_10mm.200_char_small_string.pyfora")
        
        sys.setcheckinterval(100000)

        runTest(lambda: f(1000000, 10, 2), "pyfora.string_slicing_into_vector_10mm.2_char_large_string.native")
        runTest(lambda: f(1000000, 1000, 200), "pyfora.string_slicing_into_vector_10mm.200_char_large_string.native")
        runTest(lambda: f(10000, 1000, 2), "pyfora.string_slicing_into_vector_10mm.2_char_small_string.native")
        runTest(lambda: f(10000, 100000, 200), "pyfora.string_slicing_into_vector_10mm.200_char_small_string.native")
        
        sys.setcheckinterval(100)

    def test_string_splitlines(self):
        #test a wide variety of strings with combinations of different separators
        stringsToTest = []
        for char1 in ["","a"]:
            stringsToTest.append(char1)
            for sep1 in ["\n","\r","\n\r", "\r\n", "\r\r", "\n\n", "\r\n\r"]:
                stringsToTest.append(char1 + sep1)
                for char2 in ["","b"]:
                    stringsToTest.append(char1 + sep1 + char2)
                    for sep2 in ["\n","\r","\n\r", "\r\n", "\r\r", "\n\n", "\r\n\r"]:
                        stringsToTest.append(char1 + sep1 + char2 + sep2)

        def f():
            res = []
            for shouldSplit in [True, False]:
                for candidate in stringsToTest:
                    res = res + [(candidate, candidate.splitlines(shouldSplit))]

        self.equivalentEvaluationTest(f)

    def test_string_split(self):
        #test a wide variety of strings with combinations of different separators
        stringsToTest = ["", "a", "aa", "ab", "aba", "aaa", "bbb", "abab", "abc"]
        sepsToTest = ["a","b"]

        def f():
            res = []
            for s in stringsToTest:
                for sep in sepsToTest:
                    res = res + [(s,sep, s.split(sep))]

        self.equivalentEvaluationTest(f)

    def test_string_indexing_2(self):
        def f(idx):
            x = "asdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdf"
            return x[idx]

        self.equivalentEvaluationTest(f, -1)
        self.equivalentEvaluationTest(f, -2)
        self.equivalentEvaluationTest(f, 0)
        self.equivalentEvaluationTest(f, 1)


    def test_string_comparison(self):
        def f():
            a = "a"
            b = "b"
            r1 = a < b
            r2 = a > b
            return (r1, r2)

        self.equivalentEvaluationTest(f)


    def test_string_duplication(self):
        def f():
            a = "asdf"
            r1 = a * 20
            r2 = 20 * a
            return (r1, r2)

        self.equivalentEvaluationTest(f)


    def test_string_equality_methods(self):
        def f():
            a = "val1"
            b = "val1"
            r1 = a == b
            r2 = a != b
            a = "val2"
            r3 = a == b
            r4 = a != b
            r5 = a.__eq__(b)
            r6 = a.__ne__(b)
            return (r1, r2, r3, r4, r5, r6)

        self.equivalentEvaluationTest(f)


    def test_large_strings(self):
        def f():
            a = "val1"

            while len(a) < 1000000:
                a = a + a

            return a

        self.equivalentEvaluationTest(f)


    def test_define_constant_string(self):
        x = "a string"
        with self.create_executor() as executor:
            define_x = executor.define(x)
            fora_x = define_x.result()
            self.assertIsNotNone(fora_x)


    def test_compute_string(self):
        def f():
            return "a string"

        remote = self.evaluateWithExecutor(f)
        self.assertEqual(f(), remote)
        self.assertTrue(isinstance(remote, str))


    def test_strings_1(self):
        def f():
            x = "asdf"
            return x

        self.equivalentEvaluationTest(f)
