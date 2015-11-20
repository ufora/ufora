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

import ufora.FORA.python.PurePython.ExecutorTestCases as ExecutorTestCases

import pyfora.pandas_util
import pyfora.algorithms.LinearRegression as LinearRegression
import pyfora.typeConverters.Pandas as PurePandas

import numpy
import pandas
import pandas.util.testing
import random


class InMemoryPandasTestCases(ExecutorTestCases.ExecutorTestCases):
    def checkFramesEqual(self, df1, df2):
        pandas.util.testing.assert_frame_equal(df1, df2)
        return True

    def checkSeriesEqual(self, series1, series2):
        pandas.util.testing.assert_series_equal(series1, series2)
        return True

    def test_pandas_series_basic(self):
        s = pandas.Series(range(10))

        def f():
            return s

        self.equivalentEvaluationTest(f)

    def test_pandas_dataframes_basic(self):
        df = pandas.DataFrame({'A': [1,2,3,4], 'B': [5,6,7,8]})

        def f():
            return df
            
        self.equivalentEvaluationTest(
            f,
            comparisonFunction=self.checkFramesEqual
            )

    def test_pandas_series_indexing_1(self):
        s = pandas.Series(4)

        def f(ix):
            return ix

        for ix in range(-len(s), len(s)):
            self.equivalentEvaluationTest(f, ix)

    def test_pandas_dataframe_indexing_1(self):
        df = pandas.DataFrame({'A': [1,2,3,4], 'B': [5,6,7,8]})

        def f(ix, jx):
            return df.iloc[ix, jx]

        for ix in range(-df.shape[0], df.shape[0]):
            for jx in range(-df.shape[1], df.shape[1]):
                self.equivalentEvaluationTest(
                    f, ix, jx,
                    comparisonFunction=lambda x, y: int(x) == int(y)
                    )

    def test_pandas_dataframe_indexing_2(self):
        df = pandas.DataFrame({'A': [1,2], 'B': [5,6]})

        def f(ix1, ix2, jx):
            return df.iloc[ix1:ix2, jx]

        ixes = range(-df.shape[0], df.shape[1]) + [None]
        jxes = range(-df.shape[1], df.shape[1])

        for ix1 in ixes:
            for ix2 in ixes:
                for jx in jxes:
                    self.equivalentEvaluationTest(
                        f, ix1, ix2, jx,
                        comparisonFunction=lambda x, y: list(x) == list(y)
                        )

    def test_pandas_shape(self):
        df = pandas.DataFrame({'A': [1,2,3,4], 'B': [5,6,7,8]})

        self.equivalentEvaluationTest(lambda: df.shape)
            
    def test_pandas_dataframe_ctor_1(self):
        items = [('A', [1,2,3]), ('B', [4,5,6])]

        self.equivalentEvaluationTest(
            lambda: pandas.DataFrame(dict(items)),
            comparisonFunction=self.checkFramesEqual
            )

    def test_pandas_dataframe_ctor_2(self):
        # NOTE: this form breaks the pandas API

        col1 = [1,2,3]
        col2 = [4,5,6]
        data = [col1, col2]
        
        res = self.evaluateWithExecutor(
            lambda: pandas.DataFrame(data)
            )

        self.checkFramesEqual(
            res,
            pandas.DataFrame({
                'C0': col1,
                'C1': col2
                })
            )

    def test_pandas_dataframe_class(self):
        self.equivalentEvaluationTest(
            lambda: pandas.DataFrame,
            comparisonFunction=lambda x, y: x == y
            )

    def test_pandas_read_csv_1(self):
        # there's some weirdness with whitspace that we have to deal 
        # with, on the fora side. For example, after indenting all the 
        # lines of s here, the read csv will miss the first line
        # o_O

        s = """
A,B,C
1,2,3
4,5,6
7,8,9
10,11,12
            """

        res = self.evaluateWithExecutor(
            lambda: pyfora.pandas_util.readCsvFromString(s)
            )

        self.checkFramesEqual(
            res,
            pandas.DataFrame(
                {
                    'A': [1,4,7,10],
                    'B': [2,5,8,11],
                    'C': [3,6,9,12]
                },
                dtype=float
                )
            )

    def test_pandas_read_csv_from_s3(self):
        s = """
A,B,C
1,2,3
4,5,6
7,8,9
10,11,12
            """
        with self.create_executor() as executor:
            s3 = self.getS3Interface(executor)
            key = "test_pandas_read_csv_from_s3_key"
            s3().setKeyValue("bucketname", key, s)

            remoteCsv = executor.importS3Dataset("bucketname", key).result()

            with executor.remotely.downloadAll():
                df = pyfora.pandas_util.readCsvFromString(remoteCsv)

            self.checkFramesEqual(
                df,
                pandas.DataFrame(
                    {
                        'A': [1,4,7,10],
                        'B': [2,5,8,11],
                        'C': [3,6,9,12]
                    },
                    dtype=float
                    )
                )

    def pyfora_linear_regression_test(self):
        random.seed(42)

        nRows = 100
        x_col_1 = []
        x_col_2 = []
        y_col = []
        for _ in range(nRows):
            x1 = random.uniform(-10, 10)
            x2 = random.uniform(-10, 10)

            noise = random.uniform(-1, 1)
            y = x1 * 5 + x2 * 2 - 8 + noise

            x_col_1.append(x1)
            x_col_2.append(x2)
            y_col.append(y)

        def computeCoefficients():
            predictors = PurePandas.PurePythonDataFrame([x_col_1, x_col_2], ["x1", "x2"])
            responses = PurePandas.PurePythonDataFrame([y_col], ["y"])

            return LinearRegression.linearRegression(predictors, responses)
        
        res_python = computeCoefficients()

        res_pyfora = self.evaluateWithExecutor(computeCoefficients)

        self.assertArraysAreAlmostEqual(res_python, res_pyfora)

        df_x = pandas.DataFrame({
            'x1': x_col_1,
            'x2': x_col_2
            })
        df_y = pandas.DataFrame({
            'y': y_col
            })

        res_pandas = LinearRegression.linearRegression(df_x, df_y)

        self.assertArraysAreAlmostEqual(res_python, res_pandas)

        # verified using sklearn.linear_model.LinearRegression, on nRows = 100
        res_scikit = numpy.array([[4.96925412,  2.00279298, -7.98208391]])

        self.assertArraysAreAlmostEqual(res_python, res_scikit)

    def test_pyfora_linear_regression_1(self):
        self.pyfora_linear_regression_test()

    def test_pyfora_linear_regression_with_splitting(self):
        # note: the right way to do this is to expose _splitLimit
        # as an argument to LinearRegression.linearRegression, but a 
        # lack of named arguments in pyfora means that the code 
        # would be slightly more verbose than it should need be.

        oldSplitLimit = LinearRegression._splitLimit
        try:
            LinearRegression._splitLimit = 10
            self.pyfora_linear_regression_test()
        finally:
            LinearRegression._splitLimit = oldSplitLimit
