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
import pyfora.helpers as helpers

import boto
import logging
import os
import unittest


class OutOfProcPythonPerfTest(unittest.TestCase):
    def getTestDataBucket(self):
        aws_az_key = 'AWS_AVAILABILITY_ZONE'
        bucketName = 'ufora-test-data'
        if aws_az_key in os.environ:
            az = os.environ[aws_az_key]
            if az is not '':
                region = az[:-1]
                bucketName += '-' + region
                logging.info("Resolved az: %s, region: %s", az, region)
            else:
                logging.info("No availability zone resolved")

        return bucketName

    def create_executor(self, **kwds):
        s3 = ActualS3Interface.ActualS3InterfaceFactory()
        if 'threadsPerWorker' not in kwds:
            kwds['threadsPerWorker'] = 30
        if 'memoryPerWorkerMB' not in kwds:
            kwds['memoryPerWorkerMB'] = 40000
        
        return InMemorySimulationExecutorFactory.create_executor(s3Service=s3, **kwds)

    def test_taxi_data(self):
        bucketName = self.getTestDataBucket()
        
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    conn = boto.connect_s3()
                    bucket = conn.get_bucket(bucketName)
                    key = bucket.get_key("taxi_month_1.csv")
                    contents = key.get_contents_as_string()
                    lines = contents.split("\n")


                num_lines = len(lines)
                    
        assert False, {"num_lines": num_lines}

    def test_boto_access_1(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    res = str(boto.connect_s3)


        assert False, res

    def test_boto_access_2(self):
        with self.create_executor() as e:
            with e.remotely:
                with helpers.python:
                    conn = boto.connect_s3()
                    res = str(conn)

        assert False, res

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])

