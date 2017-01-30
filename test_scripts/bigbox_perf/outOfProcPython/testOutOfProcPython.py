#   Copyright 2016 Ufora Inc.
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
import ufora.distributed.S3.ActualS3Interface as ActualS3Interface
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.Exceptions as Exceptions
import pyfora.pure_modules.pure_pandas as PurePandas
import pyfora.helpers as helpers

import sys
import unittest
import traceback
import pandas
import os
import numpy
import resource

class OutOfProcPythonTest(unittest.TestCase):
    def create_executor(self, **kwds):
        s3 = ActualS3Interface.ActualS3InterfaceFactory()
        if 'threadsPerWorker' not in kwds:
            kwds['threadsPerWorker'] = 30
        if 'memoryPerWorkerMB' not in kwds:
            kwds['memoryPerWorkerMB'] = 40000
        
        return InMemorySimulationExecutorFactory.create_executor(s3Service=s3, **kwds)

    def test_really_out_of_proc(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    pid = os.getpid()

        self.assertTrue(pid != os.getpid())

    def test_operating_on_small_slices_of_lists(self):
        with self.create_executor() as fora:
            with fora.remotely:
                #1 billion integers
                a_list = range(1000000000)

                #the first million integers
                a_list_slice = a_list[:1000000]
                with helpers.python:
                    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))

                    sum_result = sum(a_list_slice)

                a_list = None
            
            sum_result = sum_result.toLocal().result()

            self.assertEqual(sum_result, sum(range(1000000)))

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])

