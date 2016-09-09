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

class TestJOAs(unittest.TestCase):
    def setUp(self):
        self.callbackScheduler = CallbackScheduler.singletonForTesting()
        self.runtime = Runtime.getMainRuntime()
        self.axioms = self.runtime.getAxioms()
        self.native_runtime = self.runtime.getTypedForaCompiler()
        self.vals_to_test = self.loadValuesFromFile(os.path.join(os.path.split(__file__)[0],
                                                        "AxiomJOA_test.txt"))

        self.evaluator = LocalEvaluator.LocalEvaluator(
                            lambda vdm: CumulusNative.SimpleOfflineCache(self.callbackScheduler, 1000000000),
                            10000000,
                            maxPageSizeInBytes = 100000
                            )
        self.oldEvaluator = Evaluator.swapEvaluator(self.evaluator)

        self.knownModulesAsConstantJOVs = dict()
        self.knownModulesAsConstantJOVs["builtin"] = \
                FORANative.JudgmentOnValue.Constant(FORA.builtin().implVal_)

    def tearDown(self):
        self.evaluator.teardown()
        Evaluator.swapEvaluator(self.oldEvaluator)


    def loadValuesFromFile(self, x):
        simpleParse = FORANative.SimpleParseNode.parse(open(x,"rb").read())

        tr = []
        for node in simpleParse.asSequence.nodes:
            if node.isEmpty():
                pass
            else:
                tr.append([str(x) for x in node.asSequence.nodes])
        return tr

    def getJOVTFromList(self, jovStringList):
        jovList = []
        for jovString in jovStringList:
            try:
                jovList.append(FORANative.parseStringToJOV(jovString))
            except Exception as e:
                try:
                    match = re.search(
                        "^JudgmentParseError: \(unknown identifier (\w+):",
                        str(e)
                        ).group(1)
                except Exception:
                    raise e
                if match:
                    if match in self.knownModulesAsConstantJOVs:
                        jovList.append(self.knownModulesAsConstantJOVs[match])
                    else:
                        raise e
                else:
                    raise e

        return FORANative.JOVListToJOVT(jovList)

    def getJOVStringList(self, jovtString):
        jovtString = jovtString[1:-1]
        simpleParse = FORANative.SimpleParseNode.parse(jovtString)

        tr = []
        for node in simpleParse.asSequence.nodes:
            if node.isEmpty():
                pass
            else:
                tr.append(str(node))
        return tr

    def getJOVT(self, jovtString):
        return self.getJOVTFromList(self.getJOVStringList(jovtString))

    def test_repeated_calls_to_joa(self):
        for i in range(10000):
            jovt = self.getJOVT("({Vector([{Int64}])}, `Operator, `::, {Int64})" )
            self.joa(jovt)

    def test_evals_after_calling_joa_1(self):
        jovt = self.getJOVT("(fun(...){[]::([1])}, `Call)")
        self.joa(jovt)
        FORA.eval("[[1]]")

    def test_evals_after_calling_joa_2(self):
        jovt = self.getJOVT("({Vector([])}, `Operator, `::, {Vector([{Int64}])})" )
        self.joa(jovt)
        FORA.eval("[[1]]")

    def test_joas(self):
        #"test assertions about JOAs of particular axioms"
        for item in self.vals_to_test:
            jovt = self.getJOVT(item[0])

            if len(item) == 4:
                assert item[3] == "hasSideEffects", "illegal third argument to JOA"

            expected_joa = FORANative.JudgmentOnAction(
                    FORANative.parseStringToJOR(item[1]),
                    FORANative.parseStringToJOR(item[2]),
                    True if len(item) == 4 and item[3] == "hasSideEffects" else False
                    )
            computed_joa = self.joa(jovt)
            if computed_joa:
                self.assertTrue(
                    expected_joa.resultPart() == computed_joa.resultPart(),
                    "for JOVT %s should have had JOA resultPart: %s, but had: %s" \
                                % (jovt, expected_joa.resultPart(), computed_joa.resultPart())
                    )
                #be a little more relaxed on the throwParts
                self.assertTrue(
                    expected_joa.throwPart().covers(computed_joa.throwPart()),
                    "for JOVT %s: expected JOA throwPart %s does not cover computed JOA %s" \
                        % (jovt, expected_joa.throwPart(), computed_joa.throwPart())
                )
                if len(expected_joa.throwPart()) > 0:
                    self.assertTrue(
                        len(computed_joa.throwPart()) > 0,
                        "for JOVT %s: expected JOA %s throws, but computed JOA %s does not" \
                            %(jovt, expected_joa, computed_joa)
                    )

    def joa(self, jovt):
        """
        Thinking of jovt as an axiom signature, this returns the corresponding joa
        (assuming the axiom is native or an Expansion, else we get None).
        """
        axiom = self.axioms.getAxiomByJOVT(self.native_runtime, jovt)
        if axiom.isNativeCall():
            return axiom.joa()
        elif axiom.isExpansion():
            return None
        else:
            return None

