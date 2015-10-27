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
import time
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.FORA.python.FORA as FORA
import ufora.native.FORA as FORANative
import ufora.native.CallbackScheduler as CallbackScheduler
import logging
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

callbackScheduler = CallbackScheduler.singletonForTesting()

Symbol_Call = FORANative.ImplValContainer(FORANative.makeSymbol("Call"))

class TestFuturesCliqueFinder(unittest.TestCase):
    def createCliqueFinderContext(self, text, *args):
        maxPageSizeInBytes = 32 * 1024
        vdm = FORANative.VectorDataManager(callbackScheduler, maxPageSizeInBytes)

        context = ExecutionContext.ExecutionContext(
            dataManager = vdm
            )

        argumentImplvals = []

        for a in args:
            context.evaluate(
                FORA.extractImplValContainer(FORA.eval("fun() { " + a + " }")),
                Symbol_Call
                )

            argumentImplvals.append(
                context.getFinishedResult().asResult.result
                )

        actualFunction = FORA.extractImplValContainer(
            FORA.eval(text)
            )

        context.placeInEvaluationState(
            FORANative.ImplValContainer(
                (actualFunction, Symbol_Call) + tuple(argumentImplvals)
                )
            )
        
        return context, argumentImplvals, vdm


    def createCliqueFinder(self, text, *args):
        context, argsIVs, vdm = self.createCliqueFinderContext(text, *args)

        vdm.unloadAllPossible()

        context.resume()
        
        return FORANative.CliqueFinder(context)

    @PerformanceTestReporter.PerfTest("python.cumulus.CliqueFinder.big_lm")
    def disable_big_lm(self):
        rows = 20
        cols = 20
        passes = 3

        def shouldDrop(row,col):
            return col > 1 or row < 20
        randomSeed = 1

        pageCounts = {}
        
        vecText = """
            Vector.range(%s, fun(colIx) {
                Vector.range(%s, { Vector.range(1000).paged}).sum()
                })
            """ % (cols, rows)

        context, argIVs, vdm = self.createCliqueFinderContext(
            """fun(v) { 
                    math.regression.linear.computeXTX(dataframe.DataFrame(v), splitLimit:100)
                    }""",
            vecText
            )

        vecOfVecs = argIVs[0]
        droppedPages = set()

        pageCoordinates = {}

        coordsToPage = {}

        for col in range(len(vecOfVecs)):
            vec = vecOfVecs[col]

            for row, vdid in enumerate(vec.getVectorDataIdsForSlice(0, len(vec), vdm)):
                pageCoordinates[vdid.page] = (row,col)
                coordsToPage[(row,col)] = vdid.page
                rows = max(rows, row+1)

        for col in range(cols):
            vec = vecOfVecs[col]
            for row, vdid in enumerate(vec.getVectorDataIdsForSlice(0, len(vec), vdm)):
                if shouldDrop(row,col):
                    vdm.dropPageWithoutWritingToDisk(vdid.page)
                    droppedPages.add(vdid.page)

        print "dropped ", len(droppedPages), " pages"
        
        context.resume()

        for passIx in range(3):
            def inc(d,e):
                if e not in d:
                    d[e] = 0
                d[e] += 1

            for index in range(passes):
                t0 = time.time()
                added = 0
                while time.time() - t0 < 2.0:
                    randomSeed += 1
                    
                    cliqueFinder = FORANative.CliqueFinder(context)

                    task = cliqueFinder.getRootTask()

                    cliqueFinder.searchFromTopOfTreeReturningCliquesCreated(time.time() + 2.0, randomSeed)

                    for n in task.cliques():
                        added += 1
                        for p in n:
                            inc(pageCounts, p)

                print "ix: %s. cliques: %s" % (index, added)

            pageCountsSorted = sorted(list(pageCounts.values()))

            c1 = pageCountsSorted[len(pageCountsSorted) / 4]
            c2 = pageCountsSorted[len(pageCountsSorted) * 2 / 4]
            c3 = pageCountsSorted[len(pageCountsSorted) * 3 / 4]

            if c2 <= c1:
                c2 = c1 + 1
            if c3 <= c2:
                c3 = c2 + 1


            print "rows: ", rows
            print "cols: ", cols
            print "passes: ", passes
            print
            for row in range(rows):
                print "row %3s:        "%row,
                for col in range(cols):
                    if (row,col) in coordsToPage:
                        p = coordsToPage[(row,col)]
                        if p not in pageCounts or pageCounts[p] == 0:
                            sym = ' '
                        elif pageCounts[p] < c1:
                            sym = '.'
                        elif pageCounts[p] < c2:
                            sym = '-'
                        elif pageCounts[p] < c3:
                            sym = '*'
                        else:
                            sym = '#'
                    else:
                        sym = '?'

                    print sym,
                print
            print
            print
            print
            print
            print "Total pages mentioned: ", len(pageCounts), " of ", len(pageCoordinates)

        self.assertTrue(len(pageCounts) * 2 > len(pageCoordinates))
