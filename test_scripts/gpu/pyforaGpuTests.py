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
import pyfora
import ufora.config.Setup as Setup
import ufora.FORA.python.PurePython.GpuTestCases as GpuTestCases
import ufora.FORA.python.PurePython.ExecutorTestCommon as ExecutorTestCommon
import ufora.FORA.python.FORA as FORA
import ufora.FORA.python.PurePython.InMemorySimulationExecutorFactory as \
    InMemorySimulationExecutorFactory

class PyforaGpuTests(
        unittest.TestCase,
        ExecutorTestCommon.ExecutorTestCommon,
        GpuTestCases.GpuTestCases
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


    def test_with_block_assignment_1(self):
        with self.create_executor() as fora:
            x = 5

            with fora.remotely:
                b = 4 + x

            result = b.toLocal().result()
            self.assertEqual(result, 9)

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA])

