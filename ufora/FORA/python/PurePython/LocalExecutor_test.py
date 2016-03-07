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

import ufora.FORA.python.PurePython.InMemorySimulationExecutorFactory as \
    InMemorySimulationExecutorFactory
import ufora.FORA.python.PurePython.InMemoryExecutorTestCases as \
    InMemoryExecutorTestCases
import ufora.FORA.python.PurePython.InMemoryPandasTestCases as \
    InMemoryPandasTestCases
import ufora.FORA.python.PurePython.ExecutorTestCommon as ExecutorTestCommon
import ufora.FORA.python.PurePython.NumpyTestCases as NumpyTestCases
import ufora.FORA.python.PurePython.IteratorTestCases as IteratorTestCases
import ufora.FORA.python.PurePython.BuiltinTestCases as BuiltinTestCases
import ufora.FORA.python.PurePython.ExceptionTestCases as ExceptionTestCases
import ufora.FORA.python.PurePython.MathTestCases as MathTestCases
import ufora.FORA.python.PurePython.ScipySpecialTestCases as ScipySpecialTestCases
import ufora.FORA.python.PurePython.ScipyLinalgTestCases as ScipyLinalgTestCases
import ufora.FORA.python.PurePython.LogisticRegressionTests as \
    LogisticRegressionTests
import ufora.FORA.python.PurePython.RegressionTreeTests as RegressionTreeTests
import ufora.FORA.python.PurePython.GradientBoostingTests as GradientBoostingTests
import ufora.FORA.python.PurePython.FunctionTestCases as FunctionTestCases
import ufora.FORA.python.PurePython.ListTestCases as ListTestCases
import ufora.FORA.python.PurePython.UnimplementedValuesTestCases as \
    UnimplementedValuesTestCases
import ufora.FORA.python.PurePython.TrustRegionTests as TrustRegionTests


import unittest


class TestLocalExecutor(
        unittest.TestCase,
        ExecutorTestCommon.ExecutorTestCommon,
        InMemoryExecutorTestCases.InMemoryExecutorTestCases,
        InMemoryPandasTestCases.InMemoryPandasTestCases,
        NumpyTestCases.NumpyTestCases,
        IteratorTestCases.IteratorTestCases,
        BuiltinTestCases.BuiltinTestCases,
        ExceptionTestCases.ExceptionTestCases,
        MathTestCases.MathTestCases,
        LogisticRegressionTests.LogisticRegressionTests,
        RegressionTreeTests.RegressionTreeTests,
        GradientBoostingTests.GradientBoostingTests,
        ScipySpecialTestCases.ScipySpecialTestCases,
        ScipyLinalgTestCases.ScipyLinalgTestCases,
        FunctionTestCases.FunctionTestCases,
        ListTestCases.ListTestCases,
        UnimplementedValuesTestCases.UnimplementedValuesTestCases,
        TrustRegionTests.TrustRegionTests
        ):
    @classmethod
    def setUpClass(cls):
        cls.executor = None

    @classmethod
    def tearDownClass(cls):
        if cls.executor is not None:
            cls.executor.close()

    def getS3Interface(self, executor):
        return executor.s3Interface

    @classmethod
    def create_executor(cls, allowCached=True):
        if not allowCached:
            return InMemorySimulationExecutorFactory.create_executor()
        if cls.executor is None:
            cls.executor = InMemorySimulationExecutorFactory.create_executor()
            cls.executor.stayOpenOnExit = True

        return cls.executor


