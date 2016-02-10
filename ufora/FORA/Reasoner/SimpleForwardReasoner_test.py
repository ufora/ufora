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

import unittest
import os
import re
import time

import ufora.FORA.python.FORA as FORA
import ufora.FORA.python.Evaluator.Evaluator as Evaluator
import ufora.FORA.python.Evaluator.LocalEvaluator as LocalEvaluator
import ufora.FORA.python.Runtime as Runtime
import ufora.native.FORA as FORANative
import ufora.native.Cumulus as CumulusNative
import ufora.native.CallbackScheduler as CallbackScheduler
import logging
import ufora.native.TCMalloc as TCMallocNative
import pyfora

def makeJovt(*args):
    return FORANative.JOVListToJOVT(list(args))

def symbolJov(sym):
    return FORANative.parseStringToJOV("`" + sym)

class TestSimpleForwardReasoner(unittest.TestCase):
    def setUp(self):
        self.callbackScheduler = CallbackScheduler.singletonForTesting()
        self.runtime = Runtime.getMainRuntime()
        self.axioms = self.runtime.getAxioms()
        self.compiler = self.runtime.getTypedForaCompiler()
        self.builtinsAsJOV = FORANative.JudgmentOnValue.Constant(FORA.builtin().implVal_)

        pyforaPath = os.path.join(os.path.split(pyfora.__file__)[0], "fora/purePython")
        self.purePythonAsJOV = FORANative.JudgmentOnValue.Constant(FORA.importModule(pyforaPath).implVal_)
        
        self.instructionGraph = self.runtime.getInstructionGraph()
        self.reasoner = FORANative.SimpleForwardReasoner(self.compiler, self.instructionGraph, self.axioms)
        

    def nodeAndFrameCounts(self, reasoner, frame):
        allFrames = set()
        toCheck = [frame]
        while toCheck:
            frameToCheck = toCheck.pop()
            if frameToCheck not in allFrames:
                allFrames.add(frameToCheck)
                for subframe in reasoner.subframesFor(frameToCheck).values():
                    toCheck.append(subframe)

        reachableFrames = len(allFrames)
        allFrameCount = reasoner.totalFrameCount()
        badApplyNodes = 0

        for f in allFrames:
            for n in f.unknownApplyNodes():
                badApplyNodes += 1

        return badApplyNodes, reachableFrames, reasoner.totalFrameCount()

    def dumpReasonerSummary(self, reasoner, frame):
        badApplyNodes, reachableFrames, allFrameCount = self.nodeAndFrameCounts(reasoner, frame)
        logging.info("Reaching %s of %s frames with %s bad nodes.", reachableFrames, allFrameCount, badApplyNodes)

    def test_builtin_math_isSimple(self):
        frame = self.reasoner.reasonAboutApply(makeJovt(self.builtinsAsJOV, symbolJov("Member"), symbolJov("math")))

        self.assertFrameHasConstantResult(frame)

    def reasonAboutExpression(self, expression, **variableJudgments):
        keys = sorted(list(variableJudgments.keys()))

        functionText = "fun(" + ",".join(['_'] + keys) + ") { " + expression + " }"

        frame = self.reasoner.reasonAboutApply(
            makeJovt(
                FORANative.parseStringToJOV(functionText), 
                *[FORANative.parseStringToJOV(variableJudgments[k]) 
                    if isinstance(variableJudgments[k],str) else variableJudgments[k] for k in keys]
                )
            )

        self.dumpReasonerSummary(self.reasoner, frame)

        #self.reasoner.compile(frame)

        #while self.compiler.anyCompilingOrPending():
        #    time.sleep(0.001)

        return frame

    def test_nested_iterators(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun() {
                let ix = 0
                while (ix < 10)
                    {
                    ix = ix + 1
                    if (ix % 5)
                        yield ix
                    else
                        yield ix + 1
                    }
                };
            let g = fun() {
                for ix in f() {
                    if (ix % 5)
                        yield ix
                    else
                        yield ix + 1
                    }
                };
            let h = fun() {
                for ix in g() {
                    yield ix
                    }
                }
            let i = fun() {
                for ix in h() {
                    yield ix
                    }
                }

            let res = 0
            for ix in i()
                res = res + ix
            return res
            """
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_pure_python_lt(self):
        frame = self.reasonAboutExpression(
            "purePython.PyFloat(x).__lt__(purePython.PyFloat(x+1.0)).@m",
            purePython = self.purePythonAsJOV,
            x="{Float64}"
            )
        self.assertFrameHasResultJOV(frame, "{Bool}")

    def test_pure_python_isinstance(self):
        frame = self.reasonAboutExpression(
            "purePython.IsInstance(purePython.PyFloat(1.0), purePython.PyTuple((purePython.IntType,purePython.BoolType,purePython.BoolType,purePython.BoolType,purePython.FloatType))).@m",
            purePython = self.purePythonAsJOV
            )
        self.assertFrameHasResultJOV(frame, "true")
        self.assertFrameHasConstantResult(frame)

    def test_loop_resolves(self):
        frame = self.reasonAboutExpression(
            """let res = 0; 
            while (x > 0) { 
                x = x - 1; 
                res = res + x
                }
            res""",
            x = "10"
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_loop_with_iterator(self):
        frame = self.reasonAboutExpression(
            """let res = 0; 
            let sequence = fun(x) { while (x > 0) { yield x; x = x - 1 } };
            for ix in sequence(100) {
                res = res + ix
                }
            res"""
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_tuple_matching(self):
        frame = self.reasonAboutExpression(
            """
            match (x) with (()) { 0 } ((z)) { 1 }
            """,
            x = "({Int64})"
            )

        self.assertFrameHasResultJOV(frame, "1")

    def test_nested_recursion(self):
        frame = self.reasonAboutExpression(
            """
            let sum = fun(a,b,f) { 
                let res = f(a)
                a = a + 1
                while (a<b) {
                    res = res + f(a)
                    a = a + 1
                    }
                return res
                }

            sum(0,100, fun(x) { sum(0, 100, fun(x) { x })})
            """
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_tuple_iterator(self):
        frame = self.reasonAboutExpression(
            """
            [x for x in (1,2,3)]
            """
            )

        self.assertFrameHasResultJOV(frame, "{Vector([{Int64}])}")

    def test_tuple_loop_resolves(self):
        frame = self.reasonAboutExpression(
            """let res = (); 
            while (x > 0) { 
                x = x - 1; 
                res = res + (x,)
                }
            res""",
            x = "10"
            )

        self.assertFrameHasResultJOV(frame, "(...{Int64})")

    def test_function_call_works(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x) { x + 1 };
            let g = fun(x,y) { x + y };
            let res = 0; 
            while (x > 0) { 
                x = x - 1; 
                res = res + f(x) + g(x,10)
                }
            res""",
            x = "10"
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_function_call_with_branching_works(self):
        frame = self.reasonAboutExpression(
            """
            let res = 0

            let f = fun(x) { x + 1 };
            let g = fun(x) { x + 2 };

            while (res < 1000)
                {
                let toCall = nothing

                if (res > 10)
                    toCall = f
                else   
                    toCall = g

                res = res + toCall(res)
                }

            return res
            """
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")
        self.assertTrue(len(frame.unknownApplyNodes()) == 0)

    def test_function_call_and_branching(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x) { x + 1 };
            let g = fun(x) { x + 2 };
            let res = 0; 
            while (x > 0) { 
                x = x - 1; 
                if (x % 2 == 0)
                    res = res + f(x)
                else
                    res = res + g(x)
                }
            res""",
            x = "10"
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_tuple_tracing_works(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x) { x + 1 };
            let t = ("asdf", 2)
            t[f(0)]
            """,
            x = "10"
            )

        self.assertFrameHasResultJOV(frame, "2")

    def test_simple_recursion(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x, res = 0) 
                {
                if (x == 0) 
                    return res; 
                return f(x-1,res+x) 
                };

            f(1000)
            """
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_simple_dual_recursion(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x1, x2, res = 0) 
                {
                if (x1 == 0 or x2 == 0) 
                    return res; 
                return f(x1-1,x2,res+x1) + f(x1, x2 - 1, res+x2)
                };

            f(1000, 1000)
            """
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_simple_mutual_recursion(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x1, res = 0) 
                {
                if (x1 == 0) 
                    return res; 
                return g(x1-1,res+x1)
                },
            g = fun(x2, res) {
                f(x2, res) + 2
                };

            f(1000, 1000)
            """
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_call_site_recursion(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun
                (`int ) { 0 } 
                (`str) { "asdf" }
                (`tuple) { (f(`int), f(`str)) }
                ;

            f(`tuple)
            """
            )

        self.assertFrameHasResultJOV(frame, "(0,'asdf')")

    def test_recursion_on_tuples(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x, res=()) 
                {
                if (x == 0)
                    return res
                else
                    return f(x-1,(x,res))
                };

            f(1000)
            """
            )

        self.assertFrameHasResultJOV(frame, "({Int64}, (...*))")

    def DISABLEDtest_memory_load(self):
        b0 = TCMallocNative.getBytesUsed()
        b1 = b0
        for ix in range(10000):
            self.reasonAboutExpression(
                """
                let g = fun(t) { size(t) }
                let f = fun(t) { let c = g; c((1,) + t) + c((2,) + t) + c((3,) + t) };
                let f2 = fun(t) { let c = f; c((1,) + t) + c((2,) + t) + c((3,) + t) };
                let f3 = fun(t) { let c = f2; c((1,) + t) + c((2,) + t) + c((3,) + t) };
                let f4 = fun(t) { let c = f3; c((1,) + t) + c((2,) + t) + c((3,) + t) };
                
                f4((x,))
                """, x = str(ix)
                )

            print (b1 - b0) / (ix+1) / 1024 / 1024.0, " MB per for a total of ",\
                (TCMallocNative.getBytesUsed() - b0) / 1024 / 1024.0, " MB allocated."

            b1 = TCMallocNative.getBytesUsed()

    def test_recursion_on_tuples_2(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun((), soFar) { () } 
                (x, soFar) { (x[0]+soFar,) + f(x[1,], soFar+x[0]) }

            f((1,2,3), 0)
            """
            )

        self.assertFrameHasResultJOVs(frame,"(... {Int64})")

    def test_two_layer_recursion(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x, res = 0) 
                {
                if (x == 0) 
                    return res; 
                return g(x-1,res+x) 
                },
            g = fun(x,res) { f(x,res) * 2 };

            f(1000)
            """
            )

        self.assertFrameHasResultJOV(frame, "{Int64}")

    def test_same_function_called_with_different_arguments(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(x) { 
                let res = 2; 
                while (res>0) {
                    res = res - 1; 
                    x = x + x
                    }; 
                x 
                };

            (f(10),f("asdf"))
            """
            )

        self.assertFrameHasResultJOV(frame, "({Int64},{String})")

    def test_heterogeneous_vec_of_vec(self):
        frame = self.reasonAboutExpression(
            """
            [[0],["1.0"]][0]
            """
            )

        self.assertFrameHasResultJOVs(frame, "{Vector([{Int64}])}", "{Vector([{String}])}")

    def test_vector_recursion(self):
        frame = self.reasonAboutExpression(
            """
            let f = fun(v) {
                if (size(v) == 100)
                    return v
                return f([v[0], [v[0]]])
                }
            f([0])
            """
            )

        self.assertFrameHasResultJOVs(frame, "{Vector}")

    def test_list_comprehension(self):
        frame = self.reasonAboutExpression(
            """
            [x for x in (1,2,3)]
            """
            )

        self.assertFrameHasResultJOVs(frame, "{Vector([{Int64}])}")

    def test_switch_is_exclusive_and_disjoint(self):
        frame = self.reasonAboutExpression(
            """
            match (x) with (1) { 1 } ("2") { 2 }
            """,
            x="{Int64}"
            )

        self.assertFrameHasResultJOVs(frame, "1")

    def test_alternativesWork(self):
        frame = self.reasonAboutExpression(
            """
            match (#ASDF(z:x)) with (#ASDF(z:x)) { x }
            """,
            x="{Int64}"
            )

        self.assertFrameHasResultJOVs(frame, "{Int64}")

    def test_heterogeneous_vec_of_vec_function_apply(self):
        frame = self.reasonAboutExpression(
            """
            let res = []
            let ix = 0
            let v = [[0],["1.0"]]

            while (ix < size(v))
                {
                res = res :: v[ix]
                ix = ix + 1
                }
            res
            """
            )

        self.assertFrameHasResultJOVs(frame, "{Vector([{Vector([{Int64}])}, {Vector([{String}])}])}")

    def test_tuple_function_iteration(self):
        frame = self.reasonAboutExpression(
            """
            let f1 = {_+1};
            let f2 = {_+2};
            let f3 = {_+3};
            let f4 = {_+4};
            
            let fs = (f1, f2, f3, f4);

            let res = 0

            for f in fs
                res = res + f(1)

            res
            """
            )

        self.assertFrameHasResultJOVs(frame, "14")

    def test_tuple_function_iteration2(self):
        frame = self.reasonAboutExpression(
            """
            let f1 = {_+1};
            let f2 = {_+2};
            let f3 = {_+3};
            let f4 = {_+4};
            
            let fs = (f1, f2, f3, f4);

            let res = 0

            for f in fs
                for f2 in fs
                    res = res + f(1) + f2(1)

            res
            """
            )

        self.assertTrue(len(frame.unknownApplyNodes()) > 0)

    def assertFrameHasConstantResult(self, frame):
        self.assertTrue(len(frame.exits().resultPart().vals) == 1, frame.exits())
        self.assertTrue(len(frame.exits().throwPart().vals) == 0, frame.exits())
        self.assertTrue(frame.exits().resultPart()[0].constant())
        
    def assertFrameHasResultJOV(self, frame, resultJOV):
        if isinstance(resultJOV, str):
            resultJOV = FORANative.parseStringToJOV(resultJOV)

        self.assertTrue(len(frame.exits().resultPart().vals) == 1, frame.exits())
        self.assertEqual(frame.exits().resultPart()[0], resultJOV)
        
    def assertFrameHasResultJOVs(self, frame, *resultJOVs):
        self.assertTrue(len(frame.unknownApplyNodes()) == 0)

        jovsToFind = []
        for resultJOV in resultJOVs:
            if isinstance(resultJOV, str):
                resultJOV = FORANative.parseStringToJOV(resultJOV)
            jovsToFind.append(resultJOV)
        resultJOVs = list(jovsToFind)

        for res in frame.exits().resultPart():
            self.assertTrue(res in jovsToFind, 
                "Code produced unexpected JOV: %s. Result was %s but expected %s" % 
                    (res, frame.exits().resultPart(), resultJOVs)
                )
            jovsToFind.remove(res)

        self.assertTrue(
            len(jovsToFind) == 0, 
            "Code didn't produce these jovs: %s. Produced %s instead." % 
                (jovsToFind, frame.exits().resultPart())
            )
        
    
