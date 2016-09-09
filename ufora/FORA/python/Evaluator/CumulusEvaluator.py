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

import threading
import Queue
import time
import ufora.native.FORA as ForaNative

import ufora.FORA.python.Evaluator.EvaluatorBase as EvaluatorBase
from ufora.FORA.python.Exceptions import FatalException
from ufora.FORA.python.Exceptions import ClusterException

import ufora.native.Cumulus as CumulusNative

import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager

ImplValContainer_ = ForaNative.ImplValContainer

class CumulusEvaluator(EvaluatorBase.EvaluatorBase):
    def __init__(self, callbackScheduler, cumulusGatewayFactory):
        self.vdm = VectorDataManager.constructVDM(callbackScheduler)
        self.vdm.setDropUnreferencedPagesWhenFull(True)

        self.cumulusGateway = cumulusGatewayFactory(callbackScheduler, self.vdm)
        self.lock_ = threading.RLock()
        self.curPriorityIndex = 0

        self.cumulusGateway.onCPUCountChanged = self.onCPUCountChanged
        self.cumulusGateway.onCacheLoad = self.onCacheLoad
        self.cumulusGateway.onComputationResult = self.onComputationResult
        self.currentComputationId = None

        self.results_ = Queue.Queue()

    def getVDM(self):
        """return the current VectorDataManager"""
        return self.vdm

    def teardown(self):
        self.cumulusGateway.teardown()

    def verifyConnectedToGateway(self):
        if not self.cumulusGateway.isConnected:
            raise FatalException("Connection to compute cluster has been lost.")

    def cumulusComputationDefinition(self, *args):
        terms = []

        for arg in args:
            if isinstance(arg, ImplValContainer_):
                terms.append(CumulusNative.ComputationDefinitionTerm.Value(arg, None))
            else:
                terms.append(arg.computationDefinitionTerm_)

        return CumulusNative.ComputationDefinition.Root(
            CumulusNative.ImmutableTreeVectorOfComputationDefinitionTerm(terms)
            )

    def submitComputation(self, *args):
        self.currentComputationId = self.cumulusGateway.getComputationIdForDefinition(
            self.cumulusComputationDefinition(*args)
            )

        with self.lock_:
            self.cumulusGateway.setComputationPriority(
                self.currentComputationId,
                CumulusNative.ComputationPriority(self.allocNewPriority_())
                )

    def allocNewPriority_(self):
        self.curPriorityIndex += 1
        return self.curPriorityIndex

    def onComputationResult(self, computationId, result, statistics):
        with self.lock_:
            if computationId == self.currentComputationId:
                self.results_.put(result)
                self.currentComputationId = None

    def onCPUCountChanged(self, computationSystemwideCpuAssignment):
        pass

    def onCacheLoad(self, vectorDataID):
        pass


    def verifyWorkersAvailable(self):
        if self.numberOfWorkersAvailable == 0:
            time.sleep(1.0)
            if self.numberOfWorkersAvailable == 0:
                raise ClusterException(
                    "No active cores. Please start some cores in the cluster and try again.\n" +
                    "If you already requested cores, they may still be initializing. " +
                    "Please try again in a little bit."
                    )

    @property
    def numberOfWorkersAvailable(self):
        return len(self.cumulusGateway.connectedMachines_)

    def evaluate(self, *args):
        self.verifyWorkersAvailable()
        try:
            args = self.expandIfListOrTuple(*args)

            self.submitComputation(*args)

            while True:
                try:
                    result = self.results_.get_nowait()
                    break
                except Queue.Empty:
                    pass

            return result
        except KeyboardInterrupt:
            with self.lock_:
                if self.currentComputationId is not None:
                    self.cumulusGateway.setComputationPriority(
                        self.currentComputationId,
                        CumulusNative.ComputationPriority()
                        )

                    self.currentComputationId = None

                while not self.results_.empty():
                    self.results_.get(False)

            raise



