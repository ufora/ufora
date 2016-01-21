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

import pyfora.Exceptions


import logging
import numpy
import pandas
import time
import traceback


class ExecutorTestCommon(object):
    def create_executor(self, allowCached=True):
        """Subclasses of the test harness should implement"""
        raise NotImplementedError()

    def evaluateWithExecutor(self, func, *args, **kwds):
        shouldClose = True
        if 'executor' in kwds:
            executor = kwds['executor']
            shouldClose = False
        else:
            executor = self.create_executor()

        try:
            func_proxy = executor.define(func).result()
            args_proxy = [executor.define(a).result() for a in args]
            res_proxy = func_proxy(*args_proxy).result()

            result = res_proxy.toLocal().result()
            return result
        finally:
            if shouldClose:
                executor.__exit__(None, None, None)


    def defaultComparison(self, x, y):
        if isinstance(x, basestring) and isinstance(y, basestring):
            return x == y

        if hasattr(x, '__len__') and hasattr(y, '__len__'):
            l1 = len(x)
            l2 = len(y)
            if l1 != l2:
                return False
            for idx in range(l1):
                if not self.defaultComparison(x[idx], y[idx]):
                    return False
            return True
        else:
            same = x == y and type(x) is type(y)
            if not same:
                print( "Results differed: ", x, y, ". Types are ", type(x), " and ", type(y))
            return same

    def equivalentEvaluationTest(self, func, *args, **kwds):
        comparisonFunction = self.defaultComparison
        if 'comparisonFunction' in kwds:
            comparisonFunction = kwds['comparisonFunction']

        with self.create_executor() as executor:
            t0 = time.time()
            func_proxy = executor.define(func).result()
            args_proxy = [executor.define(a).result() for a in args]
            res_proxy = func_proxy(*args_proxy).result()

            pyforaResult = res_proxy.toLocal().result()
            t1 = time.time()
            pythonResult = func(*args)
            t2 = time.time()

            self.assertTrue(
                comparisonFunction(pyforaResult, pythonResult),
                "Pyfora and python returned different results: %s != %s for %s(%s), respectively" % (
                    pyforaResult, pythonResult, func, args)
                )

            if t2 - t0 > 5.0:
                print("Pyfora took ", t1 - t0, ". python took ", t2 - t1)

        return pythonResult

    def equivalentEvaluationTestThatHandlesExceptions(self, func, *args, **kwds):
        comparisonFunction = self.defaultComparison
        if 'comparisonFunction' in kwds:
            comparisonFunction = kwds['comparisonFunction']

        with self.create_executor() as executor:
            try:
                pythonResult = func(*args)
                pythonSucceeded = True
            except Exception as ex:
                pythonSucceeded = False

            try:
                pyforaResult = self.evaluateWithExecutor(func, *args, executor=executor)
                pyforaSucceeded = True
            except pyfora.Exceptions.ComputationError as ex:
                if pythonSucceeded:
                    logging.error("Python succeeded, but pyfora threw %s for %s%s", ex, func, args)
                pyforaSucceeded = False
            except:
                logging.error("General exception in pyfora for %s%s:\n%s",
                              func, args, traceback.format_exc())
                return False

            self.assertEqual(pythonSucceeded, pyforaSucceeded,
                    "Pyfora and python returned successes: %s%s" % (func, args)
                    )
            if pythonSucceeded:
                self.assertTrue(comparisonFunction(pythonResult, pyforaResult),
                    "Pyfora and python returned different results: %s != %s for %s%s, respectively" % (
                        pyforaResult, pythonResult, func, args)
                    )
                return pythonResult

    def assertArraysAreAlmostEqual(self, m1, m2):
        self.assertTrue(
            numpy.allclose(m1, m2)
            )

    def checkFramesEqual(self, df1, df2):
        pandas.util.testing.assert_frame_equal(df1, df2)
        return True

    def checkSeriesEqual(self, series1, series2, **kwargs):
        pandas.util.testing.assert_series_equal(series1, series2, **kwargs)
        return True

