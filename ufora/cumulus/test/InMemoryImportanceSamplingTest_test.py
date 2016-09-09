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
let clip = fun(x) {
    if (x > 0.0)
        return x % 1.0
    return -x % 1.0 + 1.0
    };

//simple monte-carlo estimator
let estimateNormally = fun(samples, seed, payoffFun) {
    let count = 0
    let payoff = 0

    let it = iterator(math.random.UniformReal(0.0, 1.0, seed));

    for ix in sequence(samples)
        {
        let val = (pull it);

        payoff = payoff + payoffFun(val)
        count = count + 1
        }

    return payoff / count
    }

//importance-sampling estimator using the Metropolis algorithm (see http://en.wikipedia.org/wiki/Metropolis%E2%80%93Hastings_algorithm)
let estimateRandomWalk = fun(samples, seed, payoffFun, importanceFun, keepPositions = true) {
    let unif = iterator(math.random.UniformReal(0.0, 1.0, seed));
    let norm = iterator(math.random.Normal(0.0, 1.0, seed + 100000));

    let totalPayoff = 0.0;
    let totalWeight = 0.0;

    let curPos = 0.0

    let burnin = 1000

    let positions = []

    for ix in sequence(samples) {
        let newPos = clip(curPos + (pull norm) * 0.01);

        let acceptanceRatio = importanceFun(newPos) / importanceFun(curPos)

        let shouldMove = (pull unif) < acceptanceRatio;

        if (shouldMove)
            curPos = newPos

        if (ix > burnin)
            {
            let w0 = importanceFun(curPos)

            totalPayoff = totalPayoff + payoffFun(curPos) / w0
            totalWeight = totalWeight + 1.0

            if (keepPositions)
                positions = positions :: curPos
            }
        }

    return (totalPayoff / totalWeight, positions)
    };


//make a simple payoff function. Note that the "interesting" behavior is near 0, so
//simple monte carlo will be inefficient in computing its expected value. Of course
//we can just compute the expected value of this function without Monte Carlo (its
//value is 0.001).
let frac = 0.0001;
let simplePayoff = fun(x) { if (x < frac) 1.0 else 0.0 };

//get a bunch of estimates, in an attempt to compute the expected value of `simplePayoff`
let estimates = Vector.range(100) ~~ fun(seed) { estimateNormally(100000, seed+1, simplePayoff) }

let m1 = math.stats.mean(estimates)
let s1 = math.stats.sd(estimates);

let f = 0.0002
let X = .99 / f
let Y = (1.0 - X * f) / (1.0 - f)

// this function has expected value 1 (under uniform measure on [0,1]).
// It gives a new probability measure on [0,1] weighted heavily near the origin.
let importanceFun = fun(x) { if (x < f) X else Y }

//get a bunch of estimates using the importance-sampling random walk and plot a histogram of weights
//note that they are biased near the origin.
let (estimate, positions) = estimateRandomWalk(7000000, 1, simplePayoff, importanceFun)

histogram(positions)

// now let's use importance sampling to estimate the expected value of `simplePayoff`.
let estimates2 = Vector.range(100) ~~ fun(seed) { estimateRandomWalk(100000, seed+1, simplePayoff, importanceFun, false)[0] }

let m2 = math.stats.mean(estimates2);
let s2 = math.stats.sd(estimates2);

(m1, s1, m2,s2)




"""


class InMemoryImportanceSamplingTest(unittest.TestCase):
    def test_importanceSampling(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            importanceSampling,
            s3,
            4,
            memoryLimitMb = 1000,
            timeout=240,
            useInMemoryCache = False
            )

        self.assertTrue(result.isResult())

