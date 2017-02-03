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
import logging
import ufora.native.TCMalloc as TCMallocNative
import pyfora

def makeJovt(*args):
    return FORANative.JOVListToJOVT(list(args))

def symbolJov(sym):
    return FORANative.parseStringToJOV("`" + sym)

class TestRecursiveReasoner(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime.getMainRuntime()
        self.axioms = self.runtime.getAxioms()
        self.compiler = self.runtime.getTypedForaCompiler()
        self.builtinsAsJOV = FORANative.JudgmentOnValue.Constant(FORA.builtin().implVal_)

        pyforaPath = os.path.join(os.path.split(pyfora.__file__)[0], "fora/purePython")
        self.purePythonAsJOV = FORANative.JudgmentOnValue.Constant(FORA.importModule(pyforaPath).implVal_)

        self.reasoner = FORANative.RecursiveReasoner(self.compiler, self.axioms)

    def reasonAboutExpression(self, expression, **variableJudgments):
        keys = sorted(list(variableJudgments.keys()))

        functionText = "fun(" + ",".join(['_'] + keys) + ") { " + expression + " }"

        return self.reasoner.reasonAboutApply(
            makeJovt(
                FORANative.parseStringToJOV(functionText),
                *[FORANative.parseStringToJOV(variableJudgments[k])
                    if isinstance(variableJudgments[k],str) else variableJudgments[k] for k in keys]
                )
            )

    def test_simpleReasoning(self):
        text = """
            let x = 0
            let y = 0
            while (x < 1000000)
                {
                x = x + 1
                y = y + x
                }

            y
            """

        print self.reasonAboutExpression(text)