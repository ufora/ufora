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
import logging
import traceback
import ufora.native.Cumulus as CumulusNative
import ufora.FORA.python.FORA as FORA
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.distributed.S3.ActualS3Interface as ActualS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.Runtime as Runtime
import uuid
import os
import ufora.distributed.Storage.S3ObjectStore as S3ObjectStore
import ufora.config.Setup as Setup

callbackScheduler = CallbackScheduler.singletonForTesting()

class BigboxPerformanceTest(unittest.TestCase):
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


    def computeUsingSeveralWorkers(self, *args, **kwds):
        return InMemoryCumulusSimulation.computeUsingSeveralWorkers(*args, **kwds)

    @staticmethod
    def createObjectStore(s3Service):
        return S3ObjectStore.S3ObjectStore(
            s3Service,
            Setup.config().userDataS3Bucket,
            prefix="test_object_cache/"
            )


    def downloadTaxiData(self,
                         filecount,
                         parse=False,
                         workers=1,
                         threadsPerWorker=30,
                         downloaderThreads=8):
        s3 = ActualS3Interface.ActualS3InterfaceFactory()
        
        bucketName = self.getTestDataBucket()

        result, simulation = self.computeUsingSeveralWorkers(
            "1+1",
            s3,
            workers,
            memoryLimitMb=45 * 1024 / workers,
            threadCount=threadsPerWorker,
            returnSimulation=True,
            ioTaskThreadOverride=downloaderThreads,
            useInMemoryCache=False,
            objectStore=self.createObjectStore(s3)
            )

        try:
            dsText = (
                """let ds = """ + "+".join([
                    'datasets.s3("%s", "taxi_month_%s.csv")' % (bucketName, ix) for ix in range(1, filecount+1)
                    ]) + ";"
                )

            text = dsText + "(ds, ds.sum(), size(ds))"

            downloadTimeStart = time.time()
            result = simulation.compute(text, timeout=240)
            self.assertTrue(result.isResult())
            downloadTimeEnd = time.time()
            ds, dsSum, bytecount = result.asResult.result

            if parse:
                parseTimeStart = time.time()
                result = simulation.compute("size(parsing.csv(ds))", timeout=240, ds=ds)
                parseTimeEnd = time.time()

                self.assertTrue(result.isResult())

                PerformanceTestReporter.recordTest(
                    "python.BigBox.LargeS3.ParseTaxidata." + str(filecount),
                    parseTimeEnd - parseTimeStart,
                    None
                    )
            else:
                bytecount = bytecount.pyval
                PerformanceTestReporter.recordTest(
                    "python.BigBox.LargeS3.TaxiSecondsPerGB." + str(filecount),
                    (downloadTimeEnd - downloadTimeStart) / (bytecount / 1024 / 1024.0 / 1024.0),
                    None
                    )
        finally:
            simulation.teardown()

    def test_parseTaxiData_1(self):
        self.downloadTaxiData(1, parse=True)

    def test_downloadTaxiData_1(self):
        self.downloadTaxiData(1)

    def test_downloadTaxiData_2(self):
        self.downloadTaxiData(2)

    def test_downloadTaxiData_6(self):
        self.downloadTaxiData(6)

    def dataCreationTest(self, totalMB, workers, threadsPerWorker, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """size(Vector.range(%s, {_*_}))""" % (totalMB * 1024 * 1024 / 8)

        t0 = time.time()

        result,simulation = self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                workers,
                timeout = 120,
                memoryLimitMb = 55 * 1024 / workers,
                threadCount = threadsPerWorker,
                returnSimulation = True,
                useInMemoryCache = False
                )

        try:
            t0 = time.time()
            result = simulation.compute(text, timeout=120)
            totalTimeToReturnResult = time.time() - t0

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            simulation.teardown()

    def test_createData_4000_1_30_threads(self):
        self.dataCreationTest(4000, 1, 30, "python.BigBox.VectorRange.4000_MB_1Worker_30_threads")

    def test_createData_4000_1_2_threads(self):
        self.dataCreationTest(4000, 1, 2, "python.BigBox.VectorRange.4000_MB_1Worker_2_threads")

    def test_createData_40000_1_30_threads(self):
        self.dataCreationTest(40000, 1, 30, "python.BigBox.VectorRange.40000_MB_1Worker_30_threads")

    def test_createData_40000_1_30_threads_2(self):
        self.dataCreationTest(40000, 1, 30, "python.BigBox.VectorRange.40000_MB_1Worker_30_threads_2")

    def test_createData_40000_1_2_threads(self):
        self.dataCreationTest(40000, 1, 2, "python.BigBox.VectorRange.40000_MB_1Worker_2_threads")

    @PerformanceTestReporter.PerfTest("python.BigBox.DataAsString.byteToStringAndBack")
    def test_byteToStringAndBackInDifferentPatterns(self):
        s3 = ActualS3Interface.ActualS3InterfaceFactory()

        setupText = (
            """
            let ds = Vector.range(3000000000, {UInt8(_%100)});

            let dat = Vector.range(100, fun(block) {
                Vector.range(1000000, fun(o) { let base = block * 10000000 + o * 10; (base, base + 10) })
                });

            (ds, dat, dat.sum())
            """
            )

        setupResults, simulation = self.computeUsingSeveralWorkers(
                setupText,
                s3,
                1,
                memoryLimitMb=45 * 1024,
                threadCount=30,
                returnSimulation=True,
                ioTaskThreadOverride=8,
                useInMemoryCache=False,
                timeout=30,
                objectStore=self.createObjectStore(s3)
                )

        try:
            ds, dat, datSum = setupResults.asResult.result

            t0 = time.time()
            result = simulation.compute(
                "size(datSum ~~ { ds[_[0],_[1]].dataAsString }) == size(datSum)",
                timeout=120,
                ds=ds,
                dat=dat,
                datSum=datSum
                )
            PerformanceTestReporter.recordTest(
                "python.BigBox.DataAsString.FlatVector",
                time.time() - t0,
                None
                )

            t0 = time.time()
            result = simulation.compute(
                "size(dat ~~ {_ ~~ { ds[_[0],_[1]].dataAsString } }) == size(dat)",
                timeout=120,
                ds=ds,
                dat=dat,
                datSum=datSum
                )
            PerformanceTestReporter.recordTest(
                "python.BigBox.DataAsString.NestedVector",
                time.time() - t0,
                None
                )
        finally:
            simulation.teardown()


    @PerformanceTestReporter.PerfTest("python.BigBox.WriteToS3.3MB")
    def test_write_to_s3_3mb(self):
        self.writeToS3Test(3000000)

    @PerformanceTestReporter.PerfTest("python.BigBox.WriteToS3.50MB")
    def test_write_to_s3_50mb(self):
        self.writeToS3Test(50 * 1000 * 1000)

    @PerformanceTestReporter.PerfTest("python.BigBox.WriteToS3.200MB")
    def test_write_to_s3_200mb_multibox(self):
        self.writeToS3Test(200 * 1000 * 1000, workers=4,memoryLimitMb=100, threadCount=1)

    @PerformanceTestReporter.PerfTest("python.BigBox.WriteToS3.2GB")
    def DISABLEDtest_write_to_s3_2gb_multibox(self):
        self.writeToS3Test(1000 * 1000 * 1000, workers=4,memoryLimitMb=1000, threadCount=2)

    def writeToS3Test(self, bytecount, pageSizeOverride=1024*1024, workers=1, memoryLimitMb=45 * 1024,threadCount=30):
        text = """Vector.range(__bytecount__, {UInt8(_%100)}).paged"""

        s3 = ActualS3Interface.ActualS3InterfaceFactory()

        keyGuid = "bigbox-test-key-" + str(uuid.uuid4())
        
        try:
            setupText = text.replace('__bytecount__', str(bytecount))

            setupResults, simulation = self.computeUsingSeveralWorkers(
                setupText,
                s3,
                workers,
                memoryLimitMb=memoryLimitMb,
                threadCount=threadCount,
                returnSimulation=True,
                ioTaskThreadOverride=8,
                useInMemoryCache=False,
                timeout=30,
                objectStore=self.createObjectStore(s3),
                pageSizeOverride=pageSizeOverride
                )

            result = simulation.executeExternalIoTask(
                CumulusNative.ExternalIoTask.WriteCharBigvecToS3(
                    setupResults.asResult.result.getVectorBigvecGuid(),
                    CumulusNative.S3KeyAndCredentials(
                        self.getTestDataBucket(),
                        keyGuid,
                        "",
                        "",
                        ""
                        )
                    ),
                timeout=60
                )

            self.assertTrue(result.isSuccess(), result)

            assert s3().getKeySize(self.getTestDataBucket(), keyGuid) == bytecount
        finally:
            try:
                s3().deleteKey(self.getTestDataBucket(), keyGuid)
            except:
                logging.warn("Failed to cleanup the test key: %s", traceback.format_exc())

        



if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

