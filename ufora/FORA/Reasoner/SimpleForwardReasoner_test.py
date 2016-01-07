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

import ufora.FORA.python.FORA as FORA
import ufora.FORA.python.Evaluator.Evaluator as Evaluator
import ufora.FORA.python.Evaluator.LocalEvaluator as LocalEvaluator
import ufora.FORA.python.Runtime as Runtime
import ufora.native.FORA as FORANative
import ufora.native.Cumulus as CumulusNative
import ufora.native.CallbackScheduler as CallbackScheduler

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

    def test_builtin_math_isSimple(self):
        reasoner = FORANative.SimpleForwardReasoner(self.compiler, self.axioms)

        frame = reasoner.reason(makeJovt(self.builtinsAsJOV, symbolJov("Member"), symbolJov("math")))

        self.assertFrameHasConstantResult(frame)

    def reasonAboutExpression(self, expression, **variableJudgments):
        reasoner = FORANative.SimpleForwardReasoner(self.compiler, self.axioms)
        keys = sorted(list(variableJudgments.keys()))

        functionText = "fun(" + ",".join(['_'] + keys) + ") { " + expression + " }"

        frame = reasoner.reason(
            makeJovt(
                FORANative.parseStringToJOV(functionText), 
                *[FORANative.parseStringToJOV(variableJudgments[k]) for k in keys]
                )
            )

        return frame

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

    def test_tuple_matching(self):
        frame = self.reasonAboutExpression(
            """
            match (x) with (()) { 0 } ((z)) { 1 }
            """,
            x = "({Int64})"
            )

        self.assertFrameHasResultJOV(frame, "1")

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

    def test_recursion(self):
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

    def assertFrameHasConstantResult(self, frame):
        self.assertTrue(len(frame.exits().resultPart().vals) == 1)
        self.assertTrue(frame.exits().resultPart()[0].constant())
        
    def assertFrameHasResultJOV(self, frame, resultJOV):
        if isinstance(resultJOV, str):
            resultJOV = FORANative.parseStringToJOV(resultJOV)

        self.assertTrue(len(frame.exits().resultPart().vals) == 1, frame.exits())
        self.assertEqual(frame.exits().resultPart()[0], resultJOV)
        
    
