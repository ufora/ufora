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
import logging
import ufora.FORA.python.StatementTerm as StatementTerm
import ufora.FORA.Language.Parser_test as ParserTest
import ufora.native.FORA as ForaNative
import ufora.FORA.python.FORA as FORA

import random
import numpy as np

def hashOf(e):
    return FORA.extractImplValContainer(FORA.eval(e)).hash

class StatementTermTest(unittest.TestCase):
    def setUp(self):
        self.whitespaceInserter = ForaNative.RandomWhitespaceInserter(42)
        random.seed(1337)
        np.random.seed(42)
        
    def generateTestExpressions(self):
        return ParserTest.generateTestExpressions()

    def parseTerms(self, expression):
        return StatementTerm.StatementTerm.parseToStatementTermList(
            expression,
            ForaNative.CodeDefinitionPoint(),
            "<eval>"
            )

    def test_locations(self):
        termList = self.parseTerms("let x = 1;\nx;\nx")

        locations = [term.extractCodeLocationId() for term in termList]

        self.assertTrue(locations[1] != locations[2])

    def test_locationsWithForLoops(self):
        termList = self.parseTerms("""
                let s = 1+
                    0

                while (s) 20

                s
                """)

        locations = [term.extractCodeLocationId() for term in termList]

        self.assertTrue(locations[1] != locations[2])

    def getIds(self, terms):
        return [x.extractCodeLocationId() for x in terms]

        
    def test_locationsRobustToInsertion(self):
        termList1 = self.parseTerms("""let s = 1 + 0; s; s;""")
        termList2 = self.parseTerms("""let s = 1 + 0; 123; s; s;""")

        locations1 = self.getIds(termList1)
        locations2 = self.getIds(termList2)

        self.assertTrue(locations1 == (locations2[:1] + locations2[2:]))

    def test_locationsRobustToInsertion2(self):
        text = """
        let x = 1

        let a = %s
        let y = sum(x, 10**10 + a)
        y

        let b = 0
        let z = sum(x, 10**10 + b)
        z

        let r = (y+z+sum(0, 10**10))

        r"""

        for val1, val2 in [(10,11), (123, 124)]:
            termList1 = self.parseTerms(text % val1)
            termList2 = self.parseTerms(text % val2)

            locations1 = self.getIds(termList1)
            locations2 = self.getIds(termList2)

            self.assertTrue((locations1[:1] + locations1[2:]) == (locations2[:1] + locations2[2:]))

    def test_closureIdentities(self):
        self.assertTrue(hashOf("{_}") == hashOf("{_}"))
        self.assertTrue(hashOf("(0; {_})") == hashOf("(1; {_})"))
        self.assertTrue(hashOf("0; {_}") == hashOf("1; {_}"))
        self.assertTrue(hashOf("{_}") == hashOf("{_}; {_}"))
        self.assertTrue(hashOf("({_}, 2)[0]") == hashOf("({_}, 1)[0]"))
        self.assertTrue(hashOf("{_}; {_}") == hashOf("{_}; ({_}, 1)[0]"))

        #because one is named and another is not, they are not the same.
        self.assertTrue(hashOf("{_}") != hashOf("(let v = {_}; v)"))
        self.assertTrue(hashOf("let v = {_}; v") == hashOf("let v = {_}; (fun() { v })()"))

        #check closures within closures - order of surrounding closures doesn't matter
        self.assertTrue(hashOf("let f = fun() { {_} }; f()") == hashOf("let f = fun() { {_} }; {_}; f()"))
        self.assertTrue(hashOf("let f = fun() { {_} }; f()") == hashOf("{_}; let f = fun() { {_} }; f()"))

        #check that we are robust to interior closure changes
        self.assertTrue(hashOf("let f = fun() { {_} }; f()") == hashOf("let f = fun() { 1; {_} }; f()"))
    
    def insertRandomWhitespace(self, string):
        simpleParse = ForaNative.SimpleParseNode.parse(string)
        return \
            self.whitespaceInserter.stringifyWithRandomWhitespaceAndComments(
            simpleParse
            )

    def assertInsensitivityToWhitespace(self, exprStr):
        terms1 = self.parseTerms(exprStr)

        h1 = [term.hash() for term in terms1]
        ids1 = self.getIds(terms1)

        for ix in xrange(10):
            exprStrWithWhitespace = self.insertRandomWhitespace(exprStr)

            terms2 = self.parseTerms(exprStrWithWhitespace)
            ids2 = self.getIds(terms2)

            self.assertEqual(ids1, ids2, exprStr)

            h2 = [term.hash() for term in terms2]

            self.assertEqual(
                h1, h2, "expressions did not parse equally!\n" + 
                str(exprStr) + "\n\nvs\n\n" + str(exprStrWithWhitespace)
                )
        
    def test_insensitivityToWhitespace(self):
        testExprs = self.generateTestExpressions()
        for testExpr in testExprs:
            self.assertInsensitivityToWhitespace(testExpr)

    def generateTestStatementTerms(self):
        testExprs = self.generateTestExpressions()
        tr = []
        for ix in range(25):
            randomIndices = \
                random.sample(range(len(testExprs)), min(len(testExprs), ix + 2))
            # let's keep the values unique. we've seen that statement term
            # identities are not preserved under permutations in this case
            tr.append(list(set([testExprs[ix] for ix in randomIndices])))
            
        return tr                

    def test_identities_stable_under_appending(self):
        allTerms = self.generateTestStatementTerms()
        allExprs = self.generateTestExpressions()

        for subsetOfTerms in allTerms:
            self.assertIdentitiesStableUnderAppending(subsetOfTerms, allExprs)

    def assertIdentitiesStableUnderAppending(self, subsetOfTerms, allExprs):
        originalTerms = self.parseTerms(';'.join(subsetOfTerms))

        originalHashes = \
            [term.hash() for term in originalTerms]

        originalCodeLocationIds = self.getIds(originalTerms)

        termsToInsert = random.sample(
            allExprs, min(len(allExprs), 10)
            )

        termsAfterInsertion = \
            self.parseTerms(';'.join(subsetOfTerms + termsToInsert))

        hashesAfterInsertion = \
            [term.hash() for term in termsAfterInsertion]

        codeLocationIdsAfterInsertion = self.getIds(termsAfterInsertion)

        self.assertEqual(
            originalCodeLocationIds, 
            codeLocationIdsAfterInsertion[:len(originalCodeLocationIds)]
            )

        self.assertEqual(
            originalHashes,
            hashesAfterInsertion[:len(originalHashes)]
            )      

    def test_identities_independent_of_order(self):
        testStatementTerms = self.generateTestStatementTerms()
        for terms in testStatementTerms:
            self.assertIdentitiesIndependentOfOrder(terms)

    def assertIdentitiesIndependentOfOrder(self, inTerms):
        terms1 = self.parseTerms(';'.join(inTerms))

        h1 = [term.hash() for term in terms1]
        ids1 = self.getIds(terms1)

        permutation = np.random.permutation(len(h1))
        reorderedTerms = ';'.join([inTerms[ix] for ix in permutation])
        
        terms2 = self.parseTerms(reorderedTerms)
        h2 = [term.hash() for term in terms2]
        ids2 = self.getIds(terms2)

        self.assertEqual([ids1[ix] for ix in permutation], ids2, 
                         str(ix) + "\n" + str(inTerms) + "\nvs\n" + str([inTerms[ix] for ix in permutation]))

        self.assertEqual([h1[ix] for ix in permutation], h2)
        

