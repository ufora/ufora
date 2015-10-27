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
import numpy

import ufora.config.Setup as Setup
import ufora.FORA.python.Runtime as Runtime
import ufora.FORA.python.ExecutionContext as ExecutionContext
import re
from sets import Set
import ufora.native.FORA as FORANative

import ufora.native.CallbackScheduler as CallbackScheduler
callbackScheduler = CallbackScheduler.singletonForTesting()
callbackSchedulerFactory = callbackScheduler.getFactory()

NUM_RANDOM_VALUES_TO_TEST = 5

#NOTE: this test needs to not hit the FORA interpreter, since it tests very basic functionality.
#if stuff is broken in here, then the rest of FORA will break before we can even get in here.

#a list of lists. Each list contains a sequence of strings that parse to judgments, and then
#an optional sequence of lists. Every judgment covers every judgment to its right as well as
#every element of every list to its right.
#each list at the same level is expected to contain values that are disjoint from each other
coverageTree = [
    "*",
    ["{AnyConstant}",
        ["{JOV}",
            [	["Int16"],
                ["Int32"],
                ["Int64"],
                ["MutableVector(Anything)"],
                ["UInt8"],
                ["UInt16"],
                ["UInt32"],
                ["UInt64"],
                ["Bool"],
                ["Float32"],
                ["Float64"],
                ["String"],
                ["Tag"],
                ["jovof 10"],
                ["jovof 'hello' "]
                ]
            ],
        ["{Union([{Float}, {Integer}, {String}])}",
            ["{Union([{Int64},{Float64},{Float32},{String}])}", [
                ["{Union([{Int64},{Float64}])}", [
                    ["{Int64}", [["1"],["2"],["100"]]],
                    ["{Float64}", [["1.0"],["2.0"],["100.0"]]]
                    ]],
                ["{Union([{Float32},{String}])}", [
                    ["{Float32}", [["1.0f32"],["2.0f32"],["100.0f32"]]],
                    ["{String}", ' "ASDF" ']
                    ]]
                ]],
            ["{Int16}", [["1s16"],["2s16"],["100s16"]]],
            ["{UInt16}", [["1u16"],["2u16"],["100u16"]]],
            ["{Int32}", [["1s32"],["2s32"],["100s32"]]],
            ["{UInt32}", [["1u32"],["2u32"],["100u32"]]],
            ["{UInt64}", [["1u"],["2u"],["100u"]]]
            ],
        ["{Tag}", ' #ASDF '],
        ["{Symbol}", ' `ASDF '],
        ["(... {AnyConstant})",
            ["({Int64}, ... {AnyConstant})",
                "({Int64}, {Int32}, ...{Float64})",
                "(1,{Int32},4.0,5.0, ... 7.0)",
                "(1,5s32, 4.0, 5.0, 7.0, 7.0, 7.0)"
                ],
            ["(... (... {AnyConstant}))",
                "(... ({String}, {String}))",
                "( ('asdf', 'asdf2'), ('asdf3', {String}) )"
                ],
            ["({Vector([{Int64}])}, {Vector([{Float64}])})"
                ],
            ["({Vector([{Vector([{Int64}])}])})",
                "({Vector([])})"
                ],
            ],
        ["{Vector([{AnyConstant}])}",
            [	"{Vector([({Int32}, {Int32})])}",
                "{Vector([])}",
                ],
            ],
        ["{Alternative(*, {AnyConstant})}",
            "{Alternative(`Hello, {Int64})}",
            "{Alternative(`Hello, 3)}",
            ]
        ],
    [
        "{AnyMutable}",
        "{MutableVector(jovsbelow *)}",
        [	["{MutableVector(Anything)}"],
            ["{MutableVector(Int64)}"],
            ["{MutableVector(jovof ({Int64}, *))}"],
            ["{MutableVector(jovof ({Int64}, {Int64}))}"]
            ]
        ]
    ]

def toJOV(x):
    if isinstance(x, str):
        try:
            return FORANative.parseStringToJOV(x)
        except:
            assert False, "Failed to parse %s" % x
    return x

class TestJudgmentOnValue(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime.getMainRuntime()
        self.axioms = self.runtime.getAxioms()
        self.native_runtime = self.runtime.getTypedForaCompiler()

        symbol_strings_set = Set()
        self.symbol_strings = []
        for i in range(self.axioms.axiomCount):
            sig = str(self.axioms.getAxiomGroupByIndex(i).signature())
            for j in [l.strip(' ') for l in sig.strip("()").split(',')]:
                if re.search('^`', j):
                    if j not in symbol_strings_set:
                        symbol_strings_set.add(j)
                        self.symbol_strings.append(j.strip('`'))

    def assertCovers(self, j1, j2):
        j1JOV, j2JOV = (toJOV(j1),
                    toJOV(j2))

        self.assertTrue(j1JOV.covers(j2JOV), "%s doesn't cover %s" %(j1, j2))

        if j2JOV.covers(j1JOV):
            self.assertTrue(j1JOV == j2JOV,
                "%s and %s cover each other but are different" % (j1, j2))

        if j1JOV == j2JOV:
            self.assertTrue(j2JOV.covers(j1JOV),
                "%s and %s are equal but don't cover each other" % (j1, j2))

        self.assertFalse(j1JOV.disjoint(j2JOV),
                "%s covers %s but they are also disjoint!" % (j1, j2))

        self.assertTrue(j1JOV.smallestCovering(j2JOV) == j1JOV,
            "%s and %s have smallest covering %s, which is not the first" %
                (j1JOV, j2JOV,j1JOV.smallestCovering(j2JOV)))

    def assertJOVParsesToItself(self, jov, originalString):
        """verify that we can print this, parse it, and get the same thing back"""
        try:
            reparsedJOV = FORANative.parseStringToJOV(str(jov))
        except:
            self.assertTrue(False, "%s didn't parse as a JOV" % str(jov))
            return
        self.assertTrue(reparsedJOV == jov, "%s (str='%s') reparsed as %s. hashes are %s and %s" %
                (jov, originalString, reparsedJOV, jov.hash, reparsedJOV.hash)
            )

    def treeElementCoveringTest(self, treeElt, jovsCovering, jovsDisjoint, randomJOVGenerator):
        """test the coveringTree 'treeElt'.
            jovsCovering - a list of JOV objects covering this tree
            jovsDisjoint - a list of JOV objects that are disjoint

        tests coverage across the tree, coverage for several random values, and coverage
        for several relaxations. verifies that judgments parse correctly as well
        """
        if not treeElt:
            return

        rootElement = treeElt[0]

        if isinstance(rootElement, str):
            randVals = []

            jovCurrentlyUnderTest = toJOV(rootElement)

            self.assertJOVParsesToItself(jovCurrentlyUnderTest, rootElement)

            for ix in range(NUM_RANDOM_VALUES_TO_TEST):
                rv = randomJOVGenerator.randomValue(jovCurrentlyUnderTest)
                if rv is not None:
                    randVals.append(rv)

                    #verify that FromLiveValue is working correctly
                    self.assertCovers(jovCurrentlyUnderTest, FORANative.JOVFromLiveValue(rv))

            for c in jovsCovering:
                self.assertCovers(c, rootElement)
                self.assertCovers(rootElement, rootElement)
                for randVal in randVals:
                    self.assertTrue(
                        toJOV(c).covers(randVal),
                        "%s produced %s, but %s doesn't cover it"
                            % (jovCurrentlyUnderTest, randVal, c)
                        )

                    currentJovVecEltJov = jovCurrentlyUnderTest.vectorElementJOV()
                    randValVecEltJov = FORANative.VectorElementJOVFromLiveValue(randVal)
                    if currentJovVecEltJov is not None:
                        self.assertTrue(currentJovVecEltJov.covers(randValVecEltJov))

            for d in jovsDisjoint:
                self.assertDisjoint(d, rootElement)
                for randVal in randVals:
                    self.assertTrue(
                        not toJOV(d).covers(randVal),
                        "%s produced %s, but %s, which is disjoint, covers it"
                            % (jovCurrentlyUnderTest, randVal, d)
                        )

            return self.treeElementCoveringTest(treeElt[1:],
                                                jovsCovering + [rootElement],
                                                jovsDisjoint,
                                                randomJOVGenerator
                                                )
        else:
            for subtreeIx in range(len(treeElt)):
                self.treeElementCoveringTest(
                    treeElt[subtreeIx],
                    jovsCovering,
                    jovsDisjoint +
                        [treeElt[subix][0] for subix in range(subtreeIx)
                            if subix != subtreeIx],
                    randomJOVGenerator
                    )
    def assertDoesntCover(self, j1, j2):
        self.assertFalse(
            toJOV(j1).covers(
                toJOV(j2)),
            "%s doesn't cover %s" %(j1, j2)
            )

    def assertDisjoint(self, j1, j2):
        j1JOV, j2JOV = (toJOV(j1), toJOV(j2))
        self.assertTrue(j1JOV.disjoint(j2JOV),
                "%s and %s are not disjoint" % (j1, j2))
        self.assertTrue(j2JOV.disjoint(j1JOV),
                "%s and %s are not disjoint" % (j1, j2))
        self.assertTrue(not j1JOV.covers(j2JOV),
                "%s and %s are disjoint but the first covers the second also" % (j1, j2))
        self.assertTrue(not j2JOV.covers(j1JOV),
                "%s and %s are disjoint but the first covers the second also" % (j2, j1))

    def test_cstness(self):
        self.assertTrue(toJOV("{AnyConstant}").cst is True)
        self.assertTrue(toJOV("{AnyMutable}").cst is False)
        self.assertTrue(toJOV("*").cst is None)

    def test_smallest_covering(self):
        #verify that the smallestCovering function always covers its arguments
        jovs = self.sampleJOVs()
        for j in jovs:
            for j2 in jovs:
                cover = j.smallestCovering(j2)
                self.assertCovers(cover, j)
                self.assertCovers(cover, j2)

    def assertDisjointnessRespectedByCovers(self, high, jovs):
        # test disjointness:
        # ``relax(j1).disjoint(relax(j2)) should imply j1.disjoint(j2)''
        unknown = toJOV("*")
        for i in range(high):
            i1 = numpy.random.randint(len(jovs))
            i2 = numpy.random.randint(len(jovs))
            jov1 = jovs[i1]
            jov2 = jovs[i2]
            jov1_relaxations = FORANative.JOVRelaxations(jov1)
            jov2_relaxations = FORANative.JOVRelaxations(jov2)
            i1 = numpy.random.randint(len(jov1_relaxations))
            i2 = numpy.random.randint(len(jov2_relaxations))
            jov1_relaxed = jov1_relaxations[i1]
            jov2_relaxed = jov2_relaxations[i2]
            while (jov1 != unknown and jov2 != unknown and jov1_relaxed.disjoint(jov2_relaxed)):
                self.assertTrue(jov1.disjoint(jov2))
                jov1 = jov1_relaxed
                jov2 = jov2_relaxed
                jov1_relaxations = FORANative.JOVRelaxations(jov1)
                jov2_relaxations = FORANative.JOVRelaxations(jov2)
                i1 = numpy.random.randint(len(jov1_relaxations))
                i2 = numpy.random.randint(len(jov2_relaxations))
                jov1_relaxed = jov1_relaxations[i1]
                jov2_relaxed = jov2_relaxations[i2]

    def sampleJOVTextStrings(self):
        """extract all the JOV strings from the coverage tree"""
        tr = []
        def walk(x):
            for y in x:
                if isinstance(y,str):
                    tr.append(y)
                else:
                    walk(y)
        walk(coverageTree)
        return tr

    def sampleJOVs(self):
        """extract all the JOV strings from the coverage tree"""
        return [toJOV(x) for x in self.sampleJOVTextStrings()]

    def test_sampleJOVTextStrings_parse_correctly(self):
        def parsesOK(jovText):
            try:
                toJOV(jovText)
                return True
            except:
                return False
        for j in self.sampleJOVTextStrings():
            self.assertTrue(parsesOK(j), "JOV string " + j + " failed to parse")

    def test_covers(self):
        vdm = FORANative.VectorDataManager(
                            callbackScheduler,
                            Setup.config().maxPageSizeInBytes
                            )

        context = ExecutionContext.ExecutionContext(dataManager = vdm)

        randomJOVGenerator = FORANative.RandomJOVGenerator(0, context)

        self.treeElementCoveringTest(coverageTree, [], [], randomJOVGenerator)

    def test_relaxations(self):
        # tests coverings:
        # ``relax(jov).covers(jov) should be true''
        jovs = self.sampleJOVs()

        numpy.random.seed(42)
        self.assertDisjointnessRespectedByCovers(5555, jovs)
        unknown = toJOV("*")
        for jov in jovs:
            relaxations = FORANative.JOVRelaxations(jov)
            for r in relaxations:
                self.assertTrue(r.covers(jov))
            current_jov = jov
            while (current_jov != unknown):
                relaxations_of_current_jov = FORANative.JOVRelaxations(current_jov)
                j = numpy.random.randint(len(relaxations_of_current_jov))
                random_relaxation = relaxations_of_current_jov[j]
                self.assertTrue(random_relaxation.covers(current_jov))
                currentVecEltJov = current_jov.vectorElementJOV()
                random_relaxationVecEltJov = random_relaxation.vectorElementJOV()
                if random_relaxationVecEltJov is not None:
                    self.assertTrue(random_relaxationVecEltJov.covers(currentVecEltJov))
                current_jov = random_relaxation

    def _test_jov_random_value(self):
        vdmSimple = None # Required to pass lint check - represents a bug

        context = ExecutionContext.ExecutionContext(
            32 * 1024,
            False,
            False,
            vdmSimple
            )
        jovs = self.sampleJOVs()
        randomJOVGenerator = FORANative.RandomJOVGenerator(
                                0, context).symbolStrings(self.symbol_strings)
        for jov in jovs:
            for i in range(100):
                random_value = randomJOVGenerator.randomValue(jov)
                if random_value != None:
                    self.assertTrue(jov.covers(random_value),
                        "jov %s doesn't cover %s, but generated it as a random value!" %
                            (jov, random_value)
                        )

    def _test_vectorElementJOV_VectorElementJOVFromLiveValue_compatibility(self):
        vdmSimple = None # Required to pass lint check - represents a bug

        jovs = self.sampleJOVs()
        numpy.random.seed(42)

        context = ExecutionContext.ExecutionContext(
            32 * 1024,
            False,
            False,
            vdmSimple
            )

        randomJOVGenerator = FORANative.RandomJOVGenerator(0,
                                context).symbolStrings(self.symbol_strings)

        for jov in jovs:
            for i in range(100):
                random_value = randomJOVGenerator.randomValue(jov)
                if random_value != None:
                    vectorElementJOVFromLiveValue = \
                        FORANative.VectorElementJOVFromLiveValue(random_value)
                    vectorElementJOVFromJOV = \
                        FORANative.JOVFromLiveValue(random_value).vectorElementJOV()
                    if vectorElementJOVFromLiveValue != vectorElementJOVFromJOV:
                        print "rand_val = %s" \
                            % random_value
                        print "vectorElementJOVFromLiveValue = %s" \
                                % vectorElementJOVFromLiveValue
                        print "vectorElementJOVFromJOV = %s" \
                                % vectorElementJOVFromJOV
                        print "JOVFromLiveValue = %s" \
                                % FORANative.JOVFromLiveValue(random_value)
                    self.assertEqual(vectorElementJOVFromLiveValue, vectorElementJOVFromJOV)

    def test_jov_unions_parsing(self):
        self.assertTrue(toJOV("{Union([{Int64},{Float64}])}").isUnion())
        self.assertTrue(toJOV("{Union([{Int64},nothing])}").isUnion())
        self.assertTrue(toJOV("{Union([{Int64}])}") == toJOV("{Int64}"))

        with self.assertRaises(Exception):
            toJOV("{Union([])}")

    def test_jov_unions_coverage(self):
        intAndFloat = toJOV("{Union([{Int64},{Float64}])}")
        intAndNothing = toJOV("{Union([{Int64},nothing])}")

        f = toJOV("{Float64}")
        i = toJOV("{Int64}")
        n = toJOV("nothing")

        self.assertTrue(intAndFloat.covers(f))
        self.assertTrue(intAndFloat.covers(i))
        self.assertFalse(intAndFloat.covers(n))

        self.assertFalse(intAndNothing.covers(f))
        self.assertTrue(intAndNothing.covers(i))
        self.assertTrue(intAndNothing.covers(n))

        self.assertTrue(f.disjoint(intAndNothing))
        self.assertFalse(intAndFloat.disjoint(f))
        self.assertFalse(f.disjoint(intAndFloat))

