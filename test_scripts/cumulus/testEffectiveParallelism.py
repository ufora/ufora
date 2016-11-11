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
import ufora.FORA.python.FORA as FORA
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.Runtime as Runtime

callbackScheduler = CallbackScheduler.singletonForTesting()

class EffectiveParallelismTest(unittest.TestCase):
    def computeUsingSeveralWorkers(self, *args, **kwds):
        return InMemoryCumulusSimulation.computeUsingSeveralWorkers(*args, **kwds)

    def test_effectiveParallelism(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #do a burn-in run
        self.computeUsingSeveralWorkers("""
                let v = Vector.range(5000000, { (1,_) } );

                let f = fun(ix) {
                    let res = 0
                    for x in sequence( (ix - 2000) >>> 0, ix )
                        res = res + size(v[x])
                    res
                    }

                Vector.range(size(v),  f).sum()

                """, s3, 2, wantsStats = True, timeout=240, memoryLimitMb=500
                )[1]

        t0 = time.time()

        stats = self.computeUsingSeveralWorkers("""
                let v = Vector.range(5000000, { (1,_) } );

                let f = fun(ix) {
                    let res = 0
                    for x in sequence( (ix - 2000) >>> 0, ix )
                        res = res + size(v[x])
                    res
                    }

                Vector.range(size(v),  f).sum()

                """, s3, 2, wantsStats = True, timeout=240, memoryLimitMb=500
                )[1]

        timeElapsed = time.time() - t0
        totalTime = stats.timeElapsed.timeSpentInInterpreter + stats.timeElapsed.timeSpentInCompiledCode
        effParallelism = totalTime / timeElapsed

        PerformanceTestReporter.recordTest(
            "python.cumulus.EffectiveParallelism.elapsed",
            timeElapsed,
            None
            )

        PerformanceTestReporter.recordTest(
            "python.cumulus.EffectiveParallelism.effectiveCores",
            effParallelism,
            {},
            units='count'
            )



if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

