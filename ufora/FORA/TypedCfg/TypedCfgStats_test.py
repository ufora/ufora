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
import ufora.FORA.python.Runtime as Runtime
import ufora.FORA.python.FORA as FORA
import ufora.native.FORA as ForaNative

class TestTypedCfgStats(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime.getMainRuntime()
        self.stats = self.runtime.getTypedCfgStats()

    def test_resolveAxiomDirectly_smallStrings(self):
        instance = ForaNative.ImplValContainer(
            ("s1", ForaNative.makeSymbol("Operator"), ForaNative.makeSymbol("+"), "s2")
            )
        jov = ForaNative.implValToJOV(instance)
        joa = self.stats.resolveAxiomDirectly(jov.getTuple())

        self.assertEqual(len(joa.throwPart()),0)
        self.assertEqual(len(joa.resultPart()),1)

        result = joa.resultPart()[0]

        self.assertEqual(result, ForaNative.parseStringToJOV('"s1s2"'))

    def test_resolveAxiomDirectly_Vector(self):
        vectorIVC = FORA.extractImplValContainer(FORA.eval("[]"))

        jov = ForaNative.parseStringToJOV(("({Vector([])}, `append, 2)"))

        joa = self.stats.resolveAxiomDirectly(jov.getTuple())

        self.assertEqual(len(joa.throwPart()),0)
        self.assertEqual(len(joa.resultPart()),1)

        result = joa.resultPart()[0]

        self.assertEqual(result, ForaNative.parseStringToJOV("{Vector([{Int64}])}"))

    def test_resolveAxiomDirectly_VeryLongComputation(self):
        vectorIVC = FORA.extractImplValContainer(FORA.eval("[]"))

        jov = ForaNative.parseStringToJOV(("({Vector([])}, `append, 2)"))

        joa = self.stats.resolveAxiomDirectly(jov.getTuple())

        self.assertEqual(len(joa.throwPart()),0)
        self.assertEqual(len(joa.resultPart()),1)

        result = joa.resultPart()[0]

        self.assertEqual(result, ForaNative.parseStringToJOV("{Vector([{Int64}])}"))

