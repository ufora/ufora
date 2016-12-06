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
import pyfora

import sys
import unittest
import traceback
import pandas
import os
import numpy
import resource
import boto

class OutOfProcPythonTest(unittest.TestCase):
    def create_executor(self, **kwds):
        s3 = ActualS3Interface.ActualS3InterfaceFactory()
        if 'threadsPerWorker' not in kwds:
            kwds['threadsPerWorker'] = 2
        if 'memoryPerWorkerMB' not in kwds:
            kwds['memoryPerWorkerMB'] = 400
        
        return InMemorySimulationExecutorFactory.create_executor(s3Service=s3, **kwds)

    def test_really_out_of_proc(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    pid = os.getpid()

        self.assertTrue(pid != os.getpid())

    def test_many_out_of_proc_calls(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                a_list = range(1000 * 1000)

                def sliceSum(a,b):
                    a_list_slice = a_list[a:b]
                    with helpers.python:
                        res = sum(a_list_slice)
                    return res

                res = sum(sliceSum(i * 1000, i*1000 + 1000) for i in xrange(1000))

        self.assertEqual(res, sum(range(1000000)))

    def test_out_of_proc_exit_throws_exception(self):
        with self.assertRaises(pyfora.InvalidPyforaOperation):
            with self.create_executor() as fora:
                with fora.remotely:
                    with helpers.python:
                        os._exit(0)

    def test_using_boto_in_external_works(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    result = str(boto.connect_s3)

        self.assertTrue('connect_s3' in result, result)

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])

