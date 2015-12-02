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

    def builtinMemberReasoner(self, name):
        jovt = makeJovt(self.builtinsAsJOV, symbolJov("Member"), symbolJov(name))
        return FORANative.SimpleForwardReasoner(self.compiler, self.axioms, jovt)

    def test_builtin_math_isSimple(self):
        reasoner = self.builtinMemberReasoner("math")
        self.assertTrue(reasoner.isSimple())
    
    def extractHierarchy(self, bundle):
        if bundle.isFilter():
            return [bundle.asFilter.ifAnyFalse] + self.extractHierarchy(bundle.asFilter.ifAllTrue)
        if bundle.isConstant():
            return [bundle.asConstant.value]

    def assertBundleHierarchy(self, bundle, *judgmentStrings):
        self.assertEqual(
            self.extractHierarchy(bundle),
            [FORANative.parseStringToJOV(x) for x in judgmentStrings]
            )

    def test_add_isSimple(self):
        jovt = makeJovt(
            FORANative.parseStringToJOV(
                "fun(_,_,f,x,y) { f(x,y) }"
                ), 
            symbolJov("Call"),
            FORANative.parseStringToJOV("fun(_,_,x,y) { x+y }"),
            FORANative.parseStringToJOV("1"),
            FORANative.parseStringToJOV("2")
            )

        reasoner = FORANative.SimpleForwardReasoner(self.compiler, self.axioms, jovt)

        self.assertTrue(reasoner.isSimple())

        #the bundle should have a sequence of values from "*" to "{int64}" to "3"
        self.assertBundleHierarchy(reasoner.simpleResult().resultBundle, "*", "{Int64}","3")

    def test_multiple_adds(self):
        jovt = makeJovt(
            FORANative.parseStringToJOV(
                "fun(_,_,x,y) { x+x+y }"
                ), 
            symbolJov("Call"),
            FORANative.parseStringToJOV("1"),
            FORANative.parseStringToJOV("2")
            )

        reasoner = FORANative.SimpleForwardReasoner(self.compiler, self.axioms, jovt)

        self.assertTrue(reasoner.isSimple())

        self.assertBundleHierarchy(reasoner.simpleResult().resultBundle, "*", "{Int64}","4")

    def test_add_three_things(self):
        jovt = makeJovt(
            FORANative.parseStringToJOV(
                "fun(_,_,x,y,z) { x+y+z }"
                ), 
            symbolJov("Call"),
            FORANative.parseStringToJOV("1"),
            FORANative.parseStringToJOV("2"),
            FORANative.parseStringToJOV("3")
            )

        reasoner = FORANative.SimpleForwardReasoner(self.compiler, self.axioms, jovt)

        self.assertTrue(reasoner.isSimple())
        self.assertBundleHierarchy(reasoner.simpleResult().resultBundle, "*", "{Int64}","6")
