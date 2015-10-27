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
import logging
import ufora.test.InMemoryCluster as InMemoryCluster
import ufora.cumulus.distributed.CumulusActiveMachines as CumulusActiveMachines
import ufora.util.RetryAssert as RetryAssert
import ufora.native.Hash as HashNative
import time

class WorkerCounterListener(object):
    def __init__(self):
        self.workerCount = 0

    def onWorkerAdd(self, *args):
        self.workerCount += 1

    def onWorkerDrop(self, *args):
        self.workerCount -= 1

    def onReconnectedToSharedState(self, *args):
        pass

class TestInMemoryCluster(unittest.TestCase):
    def setUp(self):
        pass

    def dialToCount(self, cumulusCount, cluster, listener, blocking=False):
        cluster.desireNumCumuli(cumulusCount, blocking=blocking)

        self.assertTrue(
            RetryAssert.waitUntilTrue(lambda: listener.workerCount == cumulusCount, 2.0),
            "Failed to reach %s machines" % cumulusCount
            )

    def test_dialUpOne(self):
        cumulusActiveMachines = None
        cluster = InMemoryCluster.InMemoryCluster()
        try:
            listener = WorkerCounterListener()

            cumulusActiveMachines = CumulusActiveMachines.CumulusActiveMachines(
                cluster.client.getClusterName(),
                cluster.sharedStateViewFactory
                )
            cumulusActiveMachines.addListener(listener)
            cumulusActiveMachines.startService()

            self.dialToCount(1, cluster, listener)
        finally:
            if cumulusActiveMachines is not None:
                cumulusActiveMachines.stopService()
            cluster.stop()

    def test_dialUpDownOne(self):
        try:
            cluster = InMemoryCluster.InMemoryCluster()

            listener = WorkerCounterListener()

            cumulusActiveMachines = CumulusActiveMachines.CumulusActiveMachines(
                cluster.client.getClusterName(),
                cluster.sharedStateViewFactory
                )
            cumulusActiveMachines.addListener(listener)
            cumulusActiveMachines.startService()

            self.dialToCount(1, cluster, listener)
            self.dialToCount(0, cluster, listener)
        finally:
            cumulusActiveMachines.stopService()
            cluster.stop()

    def test_dialUpDown(self):
        try:
            cluster = InMemoryCluster.InMemoryCluster()

            listener = WorkerCounterListener()

            cumulusActiveMachines = CumulusActiveMachines.CumulusActiveMachines(
                cluster.client.getClusterName(),
                cluster.sharedStateViewFactory
                )
            cumulusActiveMachines.addListener(listener)
            cumulusActiveMachines.startService()

            self.dialToCount(2, cluster, listener, blocking=True)
            self.dialToCount(0, cluster, listener, blocking=True)
            self.dialToCount(4, cluster, listener, blocking=True)
            self.dialToCount(0, cluster, listener, blocking=True)
        finally:
            cumulusActiveMachines.stopService()
            cluster.stop()

    def test_cumulusReconnectSharedState(self):
        try:
            cluster = InMemoryCluster.InMemoryCluster()

            listener = WorkerCounterListener()

            cumulusActiveMachines = CumulusActiveMachines.CumulusActiveMachines(
                cluster.client.getClusterName(),
                cluster.sharedStateViewFactory
                )
            cumulusActiveMachines.addListener(listener)
            cumulusActiveMachines.startService()

            self.dialToCount(2, cluster, listener, blocking=True)

            cluster.disconnectAllWorkersFromSharedState()

            time.sleep(10.0)

            self.dialToCount(4, cluster, listener, blocking=True)

            self.assertTrue(len(cluster.cumuli), 4)

            for cumulus in cluster.cumuli:
                RetryAssert.waitUntilTrue(
                    cumulus.cumulusWorker.hasEstablishedHandshakeWithExistingMachines,
                    2.0)

            #at this point, the persistent cache should work
            persistentCacheIndex = cluster.cumuli[0].persistentCacheIndex
            self.assertTrue(persistentCacheIndex.hasConnectedView())
            self.assertTrue(persistentCacheIndex.timesViewReconnected() > 0)

            persistentCacheIndex.addPage(HashNative.Hash.sha1("page"),
                                         HashNative.ImmutableTreeSetOfHash(),
                                         1,
                                         HashNative.Hash.sha1("page"))

        finally:
            cumulusActiveMachines.stopService()
            cluster.stop()

    def test_sharedStateGoesDownWhileReconnecting(self):
        try:
            cluster = InMemoryCluster.InMemoryCluster()

            listener = WorkerCounterListener()

            cumulusActiveMachines = CumulusActiveMachines.CumulusActiveMachines(
                cluster.client.getClusterName(),
                cluster.sharedStateViewFactory
                )
            cumulusActiveMachines.addListener(listener)
            cumulusActiveMachines.startService()

            self.dialToCount(2, cluster, listener, blocking=True)

            CumulusActiveMachines.CumulusActiveMachines.reconnectViewOnDisconnectIntervalForTesting = 3.0

            cluster.disconnectAllWorkersFromSharedState()

            time.sleep(1)

            cluster.disconnectAllWorkersFromSharedState()

            time.sleep(10)

            self.dialToCount(4, cluster, listener, blocking=True)

            logging.info("SUCCESS")

        finally:
            cumulusActiveMachines.stopService()
            cluster.stop()

            CumulusActiveMachines.CumulusActiveMachines.reconnectViewOnDisconnectIntervalForTesting = None

