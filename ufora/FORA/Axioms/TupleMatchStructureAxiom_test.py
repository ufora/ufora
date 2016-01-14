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
import sys
if __name__ == "__main__":
    if '-l' in sys.argv:
        sys.argv.remove('-l')
    else:
        import ufora.native
        ufora.native.Logging.mute("Info")

import ufora.native.FORA as FORANative
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.FORA.python.Runtime as Runtime

callbackScheduler = CallbackScheduler.singletonForTesting()

ivc = FORANative.ImplValContainer
sym = FORANative.makeSymbol
tag = FORANative.makeTag


def simpleEval(*args, **kwargs):
    return ExecutionContext.simpleEval(callbackScheduler, *args, **kwargs)



class TestTupleMatchStructureAxiom(unittest.TestCase):
    def testMatchStructureCantMatchTooSmallTuple(self):
        runtime = Runtime.getMainRuntime()
        axioms = runtime.getAxioms()

        jov = FORANative.parseStringToJOV("((1,2,3),`StructureMatch,((nothing, false), (nothing, false), (nothing, false), (nothing, false)))")

        axiom = axioms.getAxiomByJOVT(runtime.getTypedForaCompiler(), jov.asTuple.jov)

        self.assertTrue(len(axiom.asNative.resultSignature.resultPart().vals) == 0)


    def test_addition_working(self):
        self.assertEqual(simpleEval(1, sym("Operator"), sym("+"), 2), 3)

    def test_function_argrouting_working(self):
        f = simpleEval(sym("Function"), sym("Call"), "fun(x,y) { x+y }")
        f = simpleEval(f, sym("Call"))
        self.assertEqual(simpleEval(f, sym("Call"), 2,3), 5)

    def test_function_defaultargs(self):
        f = simpleEval(sym("Function"), sym("Call"), "fun(x,y=3) { x+y }")
        f = simpleEval(f, sym("Call"))
        self.assertEqual(simpleEval(f, sym("Call"), 2), 5)

    def test_simple_match(self):
        self.assertEqual(simpleEval((1,2,3), sym("StructureMatch"), (tag("Extras"),)), ((1,2,3),) )

    def test_simple_match_2(self):
        self.assertEqual(simpleEval((1,), sym("StructureMatch"), (((None, False)), tag("Extras"),)), (1,()) )

    def test_simple_match__with_defaults(self):
        self.assertEqual(simpleEval((1,2,3), sym("StructureMatch"), (((None, False)), ((None, False)), ((None, True)),)), (1,2,(3,)) )

    def test_simple_match__with_defaults_2(self):
        self.assertEqual(simpleEval((1,2), sym("StructureMatch"), (((None, False)), ((None, False)), ((None, True)),)), (1,2,()) )

    def test_compound_match(self):
        self.assertEqual(simpleEval((1,2,3), sym("StructureMatch"), (((None, False)), tag("Extras"),)), (1,(2,3),) )

    def test_default_match_missing(self):
        self.assertEqual(simpleEval((), sym("StructureMatch"), (((None, True)), )), ((),) )

