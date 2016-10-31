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
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface

importanceSampling = """
let timePriceCorrel = fun(df) {
    let d1 = df("Volume").applyToColumn(name: "Volume", math.log);
    let d2 = df("Close").applyToColumn(name: "Close", math.log);

    math.regression.LinearRegression(d1, d2).coefficients()[0]
    };

let genDF = fun(ix) {
    let v1 = Vector.range(1700000, { Float64(_ % 3) + 1.0 })
    let v2 = Vector.range(1700000, { Float64(_ % 4) + 1.0 + ix })
    let v3 = Vector.range(1700000, { Float64(_ % 5) + 1.0 + ix })
    let v4 = Vector.range(1700000, { Float64(_ % 6) + 1.0 + ix })
    let v5 = Vector.range(1700000, { Float64(_ % 7) + 1.0 + ix })

    let df = dataframe.DataFrame([v1, v2, v3, v4, v5],
        columnNames: ["Volume", "Close", "High", "Low", "Open"])

    df
    }

let series = Vector.range(30) ~~ genDF

let months = [(10000 * ix, 10000 * (ix+5)) for ix in sequence(160)]

let coeffs = fun(series) {
    months ~~ fun((l,h)) {
        12; timePriceCorrel(series[l,h])
        }
    };
/*
series ~~ fun(s) {
    6; coeffs(s)
    }*/

coeffs(series[0])
"""


class BigLmOnDataframeTest(unittest.TestCase):
    def test_bigLmOnDataframe(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            importanceSampling,
            s3,
            1,
            memoryLimitMb = 4000,
            threadCount = 4,
            timeout=240,
            useInMemoryCache = False
            )

        self.assertTrue(result.isResult(), result)

