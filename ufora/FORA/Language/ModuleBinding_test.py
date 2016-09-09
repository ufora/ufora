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
import ufora.native.FORA as ForaNative
import ufora.FORA.python.ForaValue as ForaValue
import random
import time

def sourceCodeTree(args):
    if len(args) == 2:
        if args[0].endswith(".script"):
            return ForaNative.SourceCodeTree.Script(args[0][:-7], args[1])
        return ForaNative.SourceCodeTree.Module(args[0], args[1])
    return ForaNative.SourceCodeTree.Module(args[0], args[1], [sourceCodeTree(x) for x in args[2]])

def checkRandomMemberAccessesAreIdenticalSingle(v1, v2, varnameCount, depth):
    for ix in range(depth):
        var = randomVarName(varnameCount)

        v1 = v1.getObjectMember(var, 100)
        v2 = v2.getObjectMember(var, 100)

        if v1 is not None and v1.pyvalOrNone is not None:
            assert v2 is not None and v2.pyvalOrNone == v1.pyvalOrNone

        if v2 is not None and v2.pyvalOrNone is not None:
            assert v1 is not None and v1.pyvalOrNone == v2.pyvalOrNone

        if v1 is None:
            return

def checkRandomMemberAccessesAreIdentical(v1, v2, varnameCount, count=1000,depth=20):
    for ix in range(count):
        checkRandomMemberAccessesAreIdenticalSingle(v1, v2, varnameCount, depth)


def randomVarName(varnameCount, varsUsed=None):
    assert varsUsed is None or len(varsUsed) < varnameCount
    while True:
        res = "v" + str(int(random.uniform(0,varnameCount)))

        if varsUsed is None or res not in varsUsed:
            if varsUsed is not None:
                varsUsed.add(res)
            return res

def randomModule(depth, memberCount, varnameCount, seed, coverFree):
    random.seed(seed)

    def generateRandomModuleDefinition(depth, memberCount,varnameCount, name = None, isRoot = False):
        members = ""
        submodules = []
        varsUsed = set()

        if name is None:
            name = "root"

        if isRoot and coverFree:
            memberCountToFind = varnameCount
        else:
            memberCountToFind = memberCount

        if not isRoot and random.uniform(0,1) < .1:
            result = randomVarName(varnameCount)
            while random.uniform(0,1) < .25:
                result = result + "." + randomVarName(varnameCount)

            #this is the 'script' path
            return (name + ".script", result)


        while len(varsUsed) < memberCountToFind:
            varname = randomVarName(varnameCount, varsUsed)

            if random.uniform(0,1) < .5 or depth < 1:
                if random.uniform(0,1) < .33:
                    result = int(random.uniform(0,100))
                else:
                    result = randomVarName(varnameCount)
                    while random.uniform(0,1) < .25:
                        result = result + "." + randomVarName(varnameCount)

                members = members + "%s: %s;" % (varname, result)
            else:
                submodules.append(
                    generateRandomModuleDefinition(depth-1,memberCount,varnameCount, varname)
                    )

        return (name, members, submodules)

    return generateRandomModuleDefinition(depth, memberCount, varnameCount, isRoot=True)


class ModuleBindingTest(unittest.TestCase):
    def parseAndBind(self, tree, freeVars = None, performDecomposition=True):
        if freeVars is None:
            freeVars = {}

        parser = ForaNative.ModuleParser()

        if not isinstance(tree, ForaNative.SourceCodeTree):
            tree = sourceCodeTree(tree)

        result = parser.parse(
            tree,
            True,
            ForaNative.CodeDefinitionPoint.ExternalFromStringList([])
            )

        return parser.bind(result, freeVars, performDecomposition)

    def test_parse_basic(self):
        result = self.parseAndBind(
            ("builtin", "f:10;", [
                ("math", "a:11;"),
                ("regression", "b:12;")
                ])
            )

        self.assertTrue(result.isModule())

        self.assertTrue(result.asModule.result.getObjectMember('z') is None)
        self.assertTrue(result.asModule.result.getObjectMember('f').pyval == 10)
        self.assertTrue(result.asModule.result.getObjectMember('math').getObjectMember('a').pyval == 11)
        self.assertTrue(result.asModule.result.getObjectMember('regression').getObjectMember('b').pyval == 12)

    def test_root_module_can_refer_to_self(self):
        result = self.parseAndBind(
            ("builtin", "f: builtin", [])
            )
        self.assertTrue(result.asModule.result is not None)

    def test_root_module_doesnt_bind_self(self):
        result = self.parseAndBind(
            ("builtin", "f: self", [])
            )

        self.assertTrue(result.asModule.result is None)

    def test_parse_empty_module(self):
        result = self.parseAndBind(
            ("asdf", "", [])
            )

        self.assertTrue(result.isModule())

    def test_parse_invariants(self):
        m1 = self.parseAndBind(
            ("builtin", """
                f: fun(0) { 'f' } (x){ g(x-1) };
                g: fun(0) { 'g' } (x){ f(x-1) };
                z: fun(x) { x }
                """, [])
            ).asModule.result

        m2 = self.parseAndBind(
            ("builtin", """
                f: fun(0) { 'f' } (x){ g(x-1) };
                g: fun(0) { 'g' } (x){ f(x-1) };
                z: fun(x) { x+1 }
                """, [])
            ).asModule.result


        self.assertTrue(m1 != m2)
        self.assertTrue(m1.getObjectMember('f') is not None)
        self.assertTrue(m2.getObjectMember('f') is not None)
        self.assertTrue(m1.getObjectMember('f') == m2.getObjectMember('f'))
        self.assertTrue(m1.getObjectMember('z') != m2.getObjectMember('z'))

    def test_parse_invariants_not_maintained_without_decomposition(self):
        m1 = self.parseAndBind(
            ("builtin", """
                f: fun(0) { 'f' } (x){ g(x-1) };
                g: fun(0) { 'g' } (x){ f(x-1) };
                z: fun(x) { x }
                """, []),
            performDecomposition=False
            ).asModule.result

        m2 = self.parseAndBind(
            ("builtin", """
                f: fun(0) { 'f' } (x){ g(x-1) };
                g: fun(0) { 'g' } (x){ f(x-1) };
                z: fun(x) { x+1 }
                """, []),
            performDecomposition=False
            ).asModule.result


        self.assertTrue(m1 != m2)
        self.assertTrue(m1.getObjectMember('f') is not None)
        self.assertTrue(m2.getObjectMember('f') is not None)
        self.assertTrue(m1.getObjectMember('f') != m2.getObjectMember('f'))
        self.assertTrue(m1.getObjectMember('z') != m2.getObjectMember('z'))

    def test_parse_errors_dont_prevent_all_entries(self):
        m1 = self.parseAndBind(
            ("builtin", """
                f: fun(0) { 'f' } (x){ g(x-1) };
                g: fun(0) { 'g' } (x){ f(x-1) };
                z: fun(x)
                """, [])
            )
        self.assertTrue(m1.isModule(), m1)

        child = m1.getMembers()['f']

        self.assertTrue(child is not None)

        self.assertTrue(child.isMember())
        self.assertTrue(child.getResultAndSymbol() is not None)

    def test_parse_errors_for_free_variables(self):
        m1 = self.parseAndBind(
            ("builtin", """
                f: fun(0) { 'f' } (x){ g(x-1) };
                g: fun(0) { 'g' } (x){ f(x-1) };
                z: fun(x) { freeVariable }
                """, [])
            )
        self.assertTrue(m1.isModule(), m1)

        child = m1.getMembers()['f']

        self.assertTrue(child is not None)
        self.assertTrue(child.isMember())
        self.assertTrue(child.getResultAndSymbol() is not None, child)

        badChild = m1.getMembers()['z']

        self.assertTrue(badChild is not None)
        self.assertTrue(badChild.isMember())
        self.assertTrue(badChild.getResultAndSymbol() is None)
        self.assertTrue(len(badChild.asMember.parseErrors) == 1)
        self.assertTrue('freeVariable' in str(badChild.asMember.parseErrors))

    def test_parse_errors_for_scripts_pointing_at_invalid_members(self):
        m1 = self.parseAndBind(
            ("builtin", "f: fun()", [
                ('a.script', '1;f')
                ])
            )
        self.assertTrue(m1.isModule(), m1)

        scriptModule = m1.getMembers()['a.module']
        self.assertTrue(scriptModule is not None)

        symbol = scriptModule.asModule.parseMetadata.asScriptModule.symbols[1]
        member = scriptModule[symbol]

        self.assertTrue(len(member.asMember.parseErrors) > 0)

    def test_free_variables_in_scripts(self):
        m1 = self.parseAndBind(
            ("builtin", "", [
                ('a.script', 'let f = fun(x) { x }; sum(0,10,f)')
                ])
            )
        self.assertTrue(m1.isModule(), m1)

    def test_module_binding(self):
        m = self.parseAndBind(
            ("builtin", "", [
                ('m1', "f: 10; g: 20"),
                ('m2', 'a: m1.f')
                ])
            )
        self.assertTrue(m.isModule())
        m1 = m.asModule.result.getObjectMember("m1")
        m2 = m.asModule.result.getObjectMember("m2")
        self.assertTrue(m1 is not None)
        self.assertTrue(m2 is not None)

        self.assertTrue(m1.getObjectMember('f', 100).pyval == 10)
        self.assertTrue(m2.getObjectMember('a', 100).pyval == 10)

    def test_module_binding_fuzzer_with_evaluation(self):
        varnameCount = 10

        for seed in range(1, 10):
            moduleDef = randomModule(
                depth=2,
                memberCount=5,
                varnameCount=varnameCount,
                seed=seed,
                coverFree=True
                )

            mDecomp = self.parseAndBind(moduleDef, performDecomposition=True)
            mRegular = self.parseAndBind(moduleDef, performDecomposition=False)

            assert mDecomp.asModule.result is not None, mDecomp
            assert mRegular.asModule.result is not None, mRegular

            #pick a random sequence of member accesses
            checkRandomMemberAccessesAreIdentical(mDecomp.asModule.result, mRegular.asModule.result, varnameCount)

    def test_module_binding_fuzzer(self):
        varnameCount = 10

        for seed in range(1, 100):
            moduleDef = randomModule(
                depth=2,
                memberCount=5,
                varnameCount=varnameCount,
                seed=seed,
                coverFree=False
                )

            mDecomp = self.parseAndBind(moduleDef, performDecomposition=True)
            mRegular = self.parseAndBind(moduleDef, performDecomposition=False)

    def test_module_binding_fuzzer_2(self):
        varnameCount = 10

        for memberCount in range(2,8):
            for seed in range(1, 100):
                moduleDef = randomModule(
                    depth=2,
                    memberCount=memberCount,
                    varnameCount=varnameCount,
                    seed=seed,
                    coverFree=False
                    )
                mDecomp = self.parseAndBind(moduleDef, performDecomposition=True)


    def test_free_variables_with_bindings(self):
        m1 = self.parseAndBind(
            ("builtin", "z: y", []),
            freeVars={'y': (ForaNative.ImplValContainer(10), None) }
            )
        self.assertTrue(m1.isModule(), m1, )
        self.assertTrue(m1.asModule.result.getObjectMember('z').pyval == 10)

    def test_script_binding(self):
        m1 = self.parseAndBind(
            ("builtin", "", [
                ('a.script', 'let f = fun(x) { x }; f(10)')
                ])
            )
        m2 = self.parseAndBind(
            ("builtin", "", [
                ('a.script', 'let f = fun(x) { x }; let g = fun(){}; f(10)')
                ])
            )

        child1Name = m1['a.module'].asModule.parseMetadata.asScriptModule.symbols[0]
        child2Name = m2['a.module'].asModule.parseMetadata.asScriptModule.symbols[0]

        child1 = m1['a.module'][child1Name]
        child2 = m2['a.module'][child2Name]

    def test_module_crossings(self):
        #binding times should be linear, not quadratic or exponential
        print self.parseAndBind(
            ("builtin", "f: (module.child, module)", [
                ("module", "child: 10", [])
                ])
            )

    def test_script_binding_performance(self):
        #binding times should be linear, not quadratic or exponential
        times = []
        for ix in [10,100]:
            t0 = time.time()

            text = "left_0: 0; right_0: 1;"

            for varIx in range(1,ix):
                text = text + "left_%s: (left_%s, right_%s);" % (varIx, varIx-1, varIx-1)
                text = text + "right_%s: (left_%s, right_%s);" % (varIx, varIx-1, varIx-1)

            m1 = self.parseAndBind(
                ("builtin", text, [])
                )

            times.append(time.time() - t0)

        self.assertTrue(times[1] < times[0] * 100)

    def test_module_names(self):
        m1 = self.parseAndBind(
            ("builtin", "", [
                ('a', 'f: 10')
                ])
            )

        moduleValue = m1.asModule.result
        innerModuleValue = m1['a'].asModule.result

        self.assertTrue(moduleValue is not None)
        self.assertTrue(innerModuleValue is not None)

        self.assertEqual(str(ForaValue.FORAValue(innerModuleValue)), "builtin.a")
        self.assertEqual(str(ForaValue.FORAValue(moduleValue)), "builtin")

    def test_script_names(self):
        m1 = self.parseAndBind(
            ("builtin", "", [
                ('a.script', '1;2')
                ])
            )

        moduleValue = m1.asModule.result
        assert 'a' in moduleValue.objectMembers

