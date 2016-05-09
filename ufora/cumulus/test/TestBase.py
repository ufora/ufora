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

import gzip
import Queue
import logging
import time
import threading

import ufora.FORA.python.FORA as FORA
import ufora.native.FORA as ForaNative
import ufora.native.Cumulus as CumulusNative
import ufora.native.Hash as HashNative

import ufora.util.Teardown as Teardown
import ufora.util.CodeCoverage as CodeCoverage

import cPickle as pickle

import ufora.native.CallbackScheduler as CallbackScheduler
callbackScheduler = CallbackScheduler.singletonForTesting()

IVC = ForaNative.ImplValContainer
callIVC = ForaNative.makeSymbol("Call")

expensiveCalculationText = """fun(count) {
    let X = [(-1.83045,-2.05459),(-1.61185,-1.1104),(-2.39371,-2.3851),(-2.30236,-1.85439),(-3.29381,-2.14036),(-2.27295,-1.9858),
        (-2.14089,-2.06091),(-0.667216,-0.470452),(-1.35343,-1.91638),(-2.32273,-2.91459),(4.04358,1.35241),(1.03174,3.38565),
        (3.84581,1.81709),(1.37791,1.8897),(2.1719,2.35836),(1.20563,2.73266),(2.42006,2.00324),(0.986196,1.38097),
        (3.11006,0.378729),(0.171622,2.46585)];
    let y = [1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,-1.,-1.,-1.,-1.,-1.,-1.,-1.,-1.,-1.,-1.];


    let DotProduct = fun(u,v) {
        let res = 0
        for ix in sequence(size(u))
            res = res + u[ix] * v[ix]
        res
        }

    let StochGDPrimalForm =
        fun( X, Y, b, lambda, N ){
            let m = size(X);
            let d = size(X[0]);

            let dims = (0,1);

            let w = dims..apply(fun(d) { 0.0 });

            let t = 1;

            for i in sequence(N){
                for j in sequence(m){

                    let jt = j;  // can be randomized
                    if ( Y[jt]*( DotProduct( X[jt],w ))< 1.0 ){

                        let newW = []

                        let xJT = X[jt];

                        w = dims..apply({
                            xJT[_] * Y[jt] / (lambda * t) * (1.0 - 1.0 / t) + w[_]
                            })

                    } else {
                        w = dims..apply({ w[_] * (1.0 - 1.0 / t) } )
                    };

                    let mult = min(1.0, 1.0/(lambda*DotProduct(w,w)));
                    w = dims..apply({w[_] * mult })
                    t=t+1;
                }
            }
            return w;
        };

    StochGDPrimalForm( X, y, 0.0, 0.01, count )
    }"""

def makeComputationDefinitionFromIVCs(*args):
    return CumulusNative.ComputationDefinition.Root(
                CumulusNative.ImmutableTreeVectorOfComputationDefinitionTerm(
                    [CumulusNative.ComputationDefinitionTerm.Value(ForaNative.ImplValContainer(x), None)
                        for x in args]
                    )
                )

def foraBrownian(x, depth):
    brownianIVC = FORA.extractImplValContainer(FORA.eval("builtin.brownian"))

    return makeComputationDefinitionFromIVCs(
                (brownianIVC, callIVC, IVC(x), IVC(depth))
                )

class CumulusTestCases(object):
    def evaluateWithGateway(self, computationDefinition, timeout=240.0):
        computationId = self.gateway.requestComputation(computationDefinition)

        try:
            return self.gateway.finalResponses.get(timeout=timeout)
        finally:
            self.gateway.deprioritizeComputation(computationId)


    @Teardown.Teardown
    def test_vecWithinVec(self):
        self.desirePublisher.desireNumberOfWorkers(4, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let v =
                        Vector.range(10) ~~ fun(x) {
                            Vector.range(1000000 + x).paged
                            };
                    v = v.paged;

                    let res = ()
                    for elt in v
                        res = res + (elt,)

                    res..apply(fun(tupElt) { tupElt.sum() })

                    'got to the end'
                    }"""
                    )
            )

        response = self.evaluateWithGateway(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        self.assertTrue(response[1].isResult())
        self.assertTrue(response[1].asResult.result.pyval == 'got to the end', response[1].asResult.result.pyval)

    @Teardown.Teardown
    def test_mixedVecOfNothingAndFloat(self):
        self.desirePublisher.desireNumberOfWorkers(4, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let v = Vector.range(1000000, fun(x) { if (x%5 == 0) nothing else x });

                    sum(0,10, fun(ix) { v.apply(fun (nothing) { nothing } (elt) { elt + ix }).sum() })
                    }"""
                    )
            )

        response = self.evaluateWithGateway(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        self.assertTrue(response[1].isResult())
        self.assertTrue(response[1].asResult.result.pyval == 4000036000000, response[1].asResult.result.pyval)


    @Teardown.Teardown
    def DISABLEDtest_repeatedCalculationOfSomethingComplex(self):
        self.desirePublisher.desireNumberOfWorkers(1, blocking=True)

        expr = FORA.extractImplValContainer(FORA.eval(expensiveCalculationText))

        def calculateTime(count):
            t0 = time.time()
            response = self.evaluateWithGateway(
                makeComputationDefinitionFromIVCs(
                    expr,
                    ForaNative.makeSymbol("Call"),
                    ForaNative.ImplValContainer(count)
                    )
                )

            self.assertTrue(response[1].isResult())

            stats = response[2]

            return (stats.timeSpentInInterpreter, stats.timeSpentInCompiler, time.time() - t0)


        perSecondValues = []

        for base in [500000]:
            for ix in range(10):
                ratio = 1.0 + ix
                interp, compiled, wallClock = calculateTime(base * ratio)
                perSecondValues.append( ((base * ratio) / wallClock / 1000000.0) )

                print base * ratio, "->", wallClock, " seconds = ", \
                    "%.2f" % ((base * ratio) / wallClock / 1000000.0), "M per second."

        #remove the first few runs
        fastest = max(perSecondValues)

        #find the point where we saturate
        saturationPoint  =0
        while saturationPoint < len(perSecondValues) and perSecondValues[saturationPoint] < fastest / 2:
            saturationPoint += 1

        if saturationPoint < len(perSecondValues):
            slowest = min(perSecondValues[saturationPoint:])
        else:
            slowest = 0.0

        self.assertTrue(slowest > fastest / 2.0, "Excessive variance in run rates: %s" % perSecondValues)


    @Teardown.Teardown
    def test_vectorOfPagedVectorApplyWithDropping(self):
        self.desirePublisher.desireNumberOfWorkers(3, blocking=True)
        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let v =
                        Vector.range(20).apply(fun(ix) {
                            Vector.range(1250000.0+ix).paged
                            }).paged
                    let lookup = fun(ix) { v[ix] }
                    Vector.range(100).apply(fun(ix) { sum(0, 10**8); cached(lookup(ix)) })
                    v
                    }"""
                    )
            )
        computation1 = self.gateway.requestComputation(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )
        try:
            response = self.gateway.finalResponses.get(timeout=60.0)
        except Queue.Empty:
            response = None
        self.assertTrue(response is not None, response)

        self.gateway.deprioritizeComputation(computation1)

        self.desirePublisher.desireNumberOfWorkers(2, blocking=True)
        expr2 = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let res = 0
                    for ix in sequence(10)
                        res = res + Vector.range(12500000+ix).sum()
                    return res
                    }"""
                    )
            )
        computation2 = self.gateway.requestComputation(
            makeComputationDefinitionFromIVCs(
                expr2,
                ForaNative.makeSymbol("Call")
                )
            )

        try:
            response = self.gateway.finalResponses.get(timeout=60.0)
        except Queue.Empty:
            response = None

        self.assertTrue(response is not None)
        self.assertTrue(response[1].isResult())

        self.gateway.deprioritizeComputation(computation2)

    @Teardown.Teardown
    def test_sortALargeVectorWithFourWorkers(self):
        self.desirePublisher.desireNumberOfWorkers(4, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let v = Vector.range(12500000, {_%3.1415926});

                    if (sorting.isSorted(sorting.sort(v))) 'sorted'
                    }"""
                    )
            )

        try:
            response = self.evaluateWithGateway(
                makeComputationDefinitionFromIVCs(
                    expr,
                    ForaNative.makeSymbol("Call")
                    ),
                timeout=120.0
                )
        except Queue.Empty:
            response = None

        if response is None:
            try:
                dumpFun = self.dumpSchedulerEventStreams
                dumpFun()
            except:
                logging.warn("Wanted to dump CumulusWorkerEvents, but couldn't");


        self.assertTrue(response is not None)
        self.assertTrue(response[1].isResult())
        self.assertTrue(response[1].asResult.result.pyval == 'sorted', response[1].asResult.result.pyval)

    @Teardown.Teardown
    def test_bigSumWithAdding(self):
        self.desirePublisher.desireNumberOfWorkers(1, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() { if (sum(0, 10**11) > 0) 'big_enough' }"""
                    )
            )

        computationId = self.gateway.requestComputation(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        time.sleep(5)

        self.desirePublisher.desireNumberOfWorkers(2, blocking=True)

        try:
            response = self.gateway.finalResponses.get(timeout=240.0)
        except Queue.Empty:
            response = None

        if response is None:
            try:
                dumpFun = self.dumpSchedulerEventStreams
                dumpFun()
            except:
                logging.warn("Wanted to dump CumulusWorkerEvents, but couldn't");

        self.assertTrue(response is not None)

        self.assertTrue(response[1].isResult())
        self.assertTrue(response[1].asResult.result.pyval == 'big_enough', response[1].asResult.result.pyval)

        self.gateway.deprioritizeComputation(computationId)

    @Teardown.Teardown
    def test_manyDuplicateCachecallsAndAdding(self):
        self.desirePublisher.desireNumberOfWorkers(2, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    Vector.range(20).papply(fun(x) {
                        x + cached(sum(0,10**11))[0]
                        })
                    }"""
                    )
            )

        computationId = self.gateway.requestComputation(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        time.sleep(5)

        self.desirePublisher.desireNumberOfWorkers(4, blocking=True)

        try:
            response = self.gateway.finalResponses.get(timeout=240.0)
        except Queue.Empty:
            response = None

        self.assertTrue(response is not None)

        self.assertTrue(response[1].isResult())

        self.gateway.deprioritizeComputation(computationId)

    @Teardown.Teardown
    def test_sortALargeVectorWithAdding(self):
        self.desirePublisher.desireNumberOfWorkers(2, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let v = Vector.range(12500000, {_%3.1415926});

                    if (sorting.isSorted(sorting.sort(v))) 'sorted_2'
                    }"""
                    )
            )

        computationId = self.gateway.requestComputation(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        time.sleep(10)

        self.desirePublisher.desireNumberOfWorkers(4, blocking=True)

        try:
            response = self.gateway.finalResponses.get(timeout=360.0)
        except Queue.Empty:
            response = None

        self.gateway.deprioritizeComputation(computationId)

        if response is None:
            try:
                dumpFun = self.dumpSchedulerEventStreams
                dumpFun()
            except:
                logging.warn("Wanted to dump CumulusWorkerEvents, but couldn't");

        self.assertTrue(response is not None)

        self.assertTrue(response[1].isResult())
        self.assertTrue(response[1].asResult.result.pyval == 'sorted_2', response[1].asResult.result.pyval)

    @Teardown.Teardown
    def test_sortALargeVectorWithRemoving(self):
        self.desirePublisher.desireNumberOfWorkers(4, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let v = Vector.range(12500000, {_%3.1415926});

                    if (sorting.isSorted(sorting.sort(v))) 'sorted_3'
                    }"""
                    )
            )

        computationId = self.gateway.requestComputation(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        time.sleep(10)

        self.desirePublisher.desireNumberOfWorkers(3, blocking=True)

        try:
            response = self.gateway.finalResponses.get(timeout=240.0)
        except Queue.Empty:
            response = None

        self.gateway.deprioritizeComputation(computationId)

        if response is None:
            try:
                dumpFun = self.dumpSchedulerEventStreams
                dumpFun()
            except:
                logging.warn("Wanted to dump CumulusWorkerEvents, but couldn't");

        self.assertTrue(response is not None)
        self.assertTrue(response[1].isResult())
        self.assertTrue(response[1].asResult.result.pyval == 'sorted_3', response[1].asResult.result.pyval)

    @Teardown.Teardown
    def test_vectorApplyWithAdding(self):
        self.desirePublisher.desireNumberOfWorkers(2, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let v = [1,2,3,4].paged;
                    let res = 0
                    sum(0,20000000000, fun(x) { v[x%4] })
                    'test_vectorApplyWithAdding'
                    }"""
                    )
            )

        computationId = self.gateway.requestComputation(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        try:
            response = self.gateway.finalResponses.get(timeout=5.0)
        except Queue.Empty:
            response = None

        self.assertTrue(response is None, response)

        self.desirePublisher.desireNumberOfWorkers(3, blocking=True)

        response = self.gateway.finalResponses.get(timeout=240.0)

        self.gateway.deprioritizeComputation(computationId)

        self.assertTrue(response[1].isResult())
        self.assertTrue(response[1].asResult.result.pyval == 'test_vectorApplyWithAdding', response[1].asResult.result.pyval)

    @Teardown.Teardown
    def test_expensive_brownian(self):
        self.desirePublisher.desireNumberOfWorkers(2, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let brownian = fun(x,t) {
                        if (t == 0)
                            return sum(0.0, x * 10.0**7.0)
                        else
                            {
                            let (l,r) = cached(brownian(x - 1, t - 1), brownian(x + 1, t - 1));
                            return sum(0.0, x * 10.0**7.0) + l + r
                            }
                        }
                    brownian(0, 5)
                    }"""
                    )
            )

        response = self.evaluateWithGateway(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        self.assertTrue(response[1].isResult())


    @Teardown.Teardown
    def test_simple_computation(self):
        self.desirePublisher.desireNumberOfWorkers(2, blocking=True)

        simpleFunc = FORA.extractImplValContainer(FORA.eval("fun(){1 + 2}"))

        response = self.evaluateWithGateway(
            makeComputationDefinitionFromIVCs(
                    simpleFunc,
                    ForaNative.makeSymbol("Call")
                    )
                )

        self.assertEqual(3, response[1].asResult.result.pyval)

    @Teardown.Teardown
    def test_sortManySmallVectors(self):
        self.desirePublisher.desireNumberOfWorkers(4, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let shouldAllBeTrue =
                    Vector.range(20, fun(o) {
                        sorting.isSorted(
                            sort(Vector.range(50000 + o, fun(x) { x / 10 }))
                            )
                        });
                    for s in shouldAllBeTrue {
                        if (not s)
                            return false
                        }

                    return true
                    }"""
                    )
            )

        response = self.evaluateWithGateway(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        self.assertTrue(response[1].isResult())
        self.assertTrue(response[1].asResult.result.pyval == True, response[1].asResult.result.pyval)

    @Teardown.Teardown
    def test_basic_sum_1_worker(self):
        self.desirePublisher.desireNumberOfWorkers(1, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    sum(0,10**10)
                    }"""
                    )
            )

        response = self.evaluateWithGateway(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        self.assertTrue(response[1].isResult())

    @Teardown.Teardown
    def test_basic_sum_2_workers(self):
        self.desirePublisher.desireNumberOfWorkers(2, blocking=True)

        expr = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    sum(0,10**10)
                    }"""
                    )
            )

        response = self.evaluateWithGateway(
            makeComputationDefinitionFromIVCs(
                expr,
                ForaNative.makeSymbol("Call")
                )
            )

        self.assertTrue(response[1].isResult())


