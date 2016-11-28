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

import ufora.native.FORA as FORANative
import ufora.FORA.python.FORA as FORA
import ufora.FORA.test as FORATestModule

import os
import traceback

def generateTestFunctions():
    testFunctions = []
    testPath = os.path.split(FORATestModule.__file__)[0]
    foraFiles = [x for x in os.listdir(testPath) if x.endswith(".fora")]

    foraModules = []
    for filename in foraFiles:
        foraModules.append(
            FORA.extractImplValContainer(
                FORA.importModule(
                    os.path.join(testPath, filename)
                    )
                )
            )

    for module in foraModules:
        for member in module.objectMembers:
            expr = module.getMemberDefinition(member)
            testFunctions.append(FORA.pythonToFORA(expr.toFunctionImplval(False)))

    return testFunctions

class FunctionToStringTest(unittest.TestCase):

    def test_repr_doesnt_die(self):
        FORA.eval("repr(math.random.MersenneTwister)")

    def assertValidParse(self, foraExpressionText, checkActualValues = False):
        result1 = FORA.eval(foraExpressionText)
        resultStr = FORA.makeSymbol("ParsableRepresentation")(result1)
        try:
            result2 = FORA.eval(resultStr)
        except:
            self.assertTrue(False,
                "Wasn't able to parse:\n**************\n%s\n*************\n\n%s"
                 % (result1, traceback.format_exc())
                )

        resultStr2 = FORA.makeSymbol("ParsableRepresentation")(result2)
        try:
            result3 = FORA.eval(resultStr2)
        except:
            self.assertTrue(False,
                "Wasn't able to parse:\n**************\n%s\n*************\n\n%s"
                 % (result2, traceback.format_exc())
                )

        if checkActualValues:
            self.assertTrue(
                    result2 == result3,
                    "Printing and parsing %s resulted in %s, which is not the same"
                    % (result2, result3)
                    )

    def assertValidStringifyAndParse(self, foraValue, checkActualValues = False):
        resultStr = FORA.makeSymbol("ParsableRepresentation")(foraValue)
        try:
            result2 = FORA.makeSymbol("ParsableRepresentation")(FORA.eval(resultStr))
        except:
            self.assertTrue(False,
                "Wasn't able to parse:\n**************\n%s\n*************\n\n%s"
                 % (resultStr, traceback.format_exc())
                )

        if checkActualValues:
            self.assertTrue(
                    FORA.eval(resultStr) == FORA.eval(result2),
                    "Printing and parsing %s resulted in %s, which is not the same."
                    % (resultStr,result2)
                    )

    def test_basic_parsing(self):
        self.assertValidParse("(,)", True)
        self.assertValidParse("(1,)", True)
        self.assertValidParse("fun(x){x}", True)
        self.assertValidParse("fun(x,y){x+y-y**y}", True)
        self.assertValidParse("let f = fun(x){if(x<1) 0 else f(x-1)+1}", True)
        self.assertValidParse("fun(x,y,z){x+y**z+(x*y-z)*x}(x){x**3-(3+x)*x}", True)
        self.assertValidParse("fun(x,y){let f=fun(x){x**2}; f(x)+y;}", True)
        self.assertValidParse("let x = 0; fun(){x}", True)
        self.assertValidParse("fun(){({10}  + 1) is (10;  1)}", True)
        self.assertValidParse("let x=10;let y=5;let g = fun(z){x+y+z};let f = fun(w){w+f(w)}")
        self.assertValidParse("let c = 3; let x = 2; let p = object{t:6}; object{w: 10 + y+c; y: 20;"
                                +" z: object{ f: x+p.t+c } }", True)

        self.assertValidParse("let c = 3; let x = 2; let p = object{t:6}; object{w: 10 + y+c; y: 20;"
                                +" z: object{ f: x+c };q: object{g: x+z+c}; p2: p}", True)

        self.assertValidParse("let c = 3; let x = 2; let p = object{t:6}; object{w: 10 + y+c; y: 20;"
                                +" q: object{g: object{k: x+z+c}}; z: object{ f: q.g +c }; p2: p}", True)

        self.assertValidParse("let p=object{f: 3; g: object{h: f}}; let o=object{f: 2;g: object{h: f+2+p.g.h;}};"
                                +" let q = object{f: 2+o.g}", True)

        self.assertValidParse("let c = 3; let x = 2; let p = object{f: object{t:6+x+c}}; object{w: p.f; y: 20;}", True)
        self.assertValidParse("let o = 6; let p = object{q:fun(){2};g:object{j:fun(){3}};h:object{k:q+g.j};"
                                +"l:fun(){h.k+o}}; p.l")

        self.assertValidParse("let o = 6; let o1 = 4; let p = object{q:fun(){2};g:object{j:fun(){3}};"
                                +"h:object{k:q+g.j};l:fun(){h.k+o+o1}}; p.l")

        self.assertValidParse("let o = 6; let o1 = 4; let p = object{q:fun(){o1};g:object{j:fun(){3}};"
                                +"h:object{k:q+g.j};l:fun(){h.k+o}}; p.l")
        #tests that let-scoping works properly
        self.assertValidParse("fun(y){let x = 1; (4; 5; 6+x; (x+3;let x=4;7) let x = 2; x + 3; x + y) x}", True)
        self.assertValidParse("fun(y){let x = 1; (let x = 2; x + 3) x+y}", True)
        self.assertValidParse("fun(y){let x = 1; (4; 5; 6+x; x+3; let x = 2; x + 3; x + y) x}", True)
        #tests that object printing can be blocked!
        self.assertValidParse("let d = {`math:math};let f = fun(x){math.sin(x)};repr(f,d)", True)
        #tests listComprehensions
        self.assertValidParse("fun(){[(x;2) for x in [1,2,3]]}", True)

    def test_printing_and_parsing_on_all_test_expressions(self):
        for testFun in generateTestFunctions():
            self.assertValidStringifyAndParse(testFun)

