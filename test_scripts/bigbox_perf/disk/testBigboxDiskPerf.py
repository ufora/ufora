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
import threading
import uuid
import shutil
import os
import tempfile
import ufora.FORA.python.FORA as FORA
import ufora.distributed.S3.ActualS3Interface as ActualS3Interface
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.Runtime as Runtime
import ufora.native.Cumulus as CumulusNative
import ufora.native.FORA as ForaNative
import ufora.native.Hash as HashNative
import ufora.distributed.Storage.S3ObjectStore as S3ObjectStore
import ufora.config.Setup as Setup

callbackScheduler = CallbackScheduler.singletonForTesting()

class BigboxDiskPerformanceTest(unittest.TestCase):
    def test_disk_scans(self):
        s3 = ActualS3Interface.ActualS3InterfaceFactory()
        objectStore = S3ObjectStore.S3ObjectStore(
            s3,
            Setup.config().userDataS3Bucket,
            prefix="test_object_cache/"
            )

        _, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            "1+1",
            s3,
            1,
            memoryLimitMb=1 * 1024,
            threadCount=30,
            returnSimulation=True,
            ioTaskThreadOverride=8,
            objectStore=objectStore,
            useInMemoryCache=False  #use an actual disk cache for this
            )

        try:
            gigabytes = 8

            t0 = time.time()

            resultVectors = []
            for ix in range(gigabytes):
                result = simulation.compute("Vector.range(125000000 + %s)" % ix, timeout=120)
                resultVectors.append(result.asResult.result)

            t1 = time.time()

            intResults = []
            for vec in resultVectors:
                result = simulation.compute("v.sum()", timeout = 120, v=vec)
                intResults.append(result.asResult.result.pyval)


            self.assertTrue(len(intResults) == gigabytes)

            PerformanceTestReporter.recordTest(
                "python.BigBox.Disk.Write.10GB",
                t1 - t0,
                None
                )

            PerformanceTestReporter.recordTest(
                "python.BigBox.Disk.WriteAndScan.%sGB" % gigabytes,
                time.time() - t0,
                None
                )
        finally:
            simulation.teardown()

    def diskThroughputTest(self, gb):
        if os.getenv("CUMULUS_DATA_DIR") is None:
            dataDir = tempfile.mkdtemp()
        else:
            dataDir = os.getenv("CUMULUS_DATA_DIR")
        dataDir = os.path.join(dataDir, str(uuid.uuid4()))

        diskCache = CumulusNative.DiskOfflineCache(
            callbackScheduler,
            dataDir,
            100 * 1024 * 1024 * 1024,
            100000
            )

        fiftyMegabytes = ForaNative.encodeStringInSerializedObject(" " * 1024 * 1024 * 50)

        logging.info("Writing to %s", dataDir)

        try:
            t0 = time.time()
            for ix in range(gb * 20):
                diskCache.store(
                    ForaNative.PageId(HashNative.Hash.sha1(str(ix)), 50 * 1024 * 1024, 50 * 1024 * 1024),
                    fiftyMegabytes
                    )

            PerformanceTestReporter.recordTest(
                "python.BigBox.Disk.Write%sGB" % gb,
                time.time() - t0,
                None
                )

            t0 = time.time()
            for ix in range(gb * 20):
                diskCache.loadIfExists(
                    ForaNative.PageId(HashNative.Hash.sha1(str(ix)), 50 * 1024 * 1024, 50 * 1024 * 1024)
                    )


            PerformanceTestReporter.recordTest(
                "python.BigBox.Disk.Read%sGB" % gb,
                time.time() - t0,
                None
                )

        finally:
            shutil.rmtree(dataDir)


    def test_disk_read_and_write_perf(self):
        if os.getenv("CUMULUS_DATA_DIR") is None:
            dataDir = tempfile.mkdtemp()
        else:
            dataDir = os.getenv("CUMULUS_DATA_DIR")
        dataDir = os.path.join(dataDir, str(uuid.uuid4()))

        diskCache = CumulusNative.DiskOfflineCache(
            callbackScheduler,
            dataDir,
            100 * 1024 * 1024 * 1024,
            100000
            )

        try:
            fiftyMegabytes = ForaNative.encodeStringInSerializedObject(" " * 1024 * 1024 * 50)

            logging.info("Writing to %s", dataDir)

            storedPageID = ForaNative.PageId(HashNative.Hash.sha1("pageId"), 50 * 1024 * 1024, 50 * 1024 * 1024)

            diskCache.store(storedPageID, fiftyMegabytes)

            t0 = time.time()

            TOTAL_SECONDS = 20.0

            totalReadBytes = [0]
            totalWriteBytes = [0]

            def readerThread():
                while time.time() - t0 < TOTAL_SECONDS:
                    diskCache.loadIfExists(storedPageID)
                    totalReadBytes[0] += 50

            def writerThread():
                ix = 0
                while time.time() - t0 < TOTAL_SECONDS:
                    ix += 1
                    diskCache.store(
                        ForaNative.PageId(HashNative.Hash.sha1(str(ix)), 50 * 1024 * 1024, 50 * 1024 * 1024),
                        fiftyMegabytes
                        )
                    totalWriteBytes[0] += 50

            threads = [
                threading.Thread(target = readerThread),
                threading.Thread(target = writerThread)
                ]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            PerformanceTestReporter.recordTest(
                "python.BigBox.Disk.ReadAndWrite.Write1GB",
                1024 / (totalWriteBytes[0] / (time.time() - t0)),
                None
                )

            PerformanceTestReporter.recordTest(
                "python.BigBox.Disk.ReadAndWrite.Read1GB",
                1024 / (totalReadBytes[0] / (time.time() - t0)),
                None
                )

        finally:
            shutil.rmtree(dataDir)

    def test_disk_throughput(self):
        self.diskThroughputTest(1)
        self.diskThroughputTest(2)
        self.diskThroughputTest(4)
        self.diskThroughputTest(8)


if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

