#   Copyright 2015-2016 Ufora Inc.
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

import logging
import threading

from ufora.BackendGateway.Observable import Observable, observable
import ufora.native.Cumulus as CumulusNative


class VectorSlice(Observable):
    def __init__(self, vector, low_index, high_index):
        self.vector = vector
        self.low_index = low_index
        self.high_index = high_index

        self.is_loaded = False
        self._vdids = None


    @observable
    def set_is_loaded(self, is_loaded):
        self.is_loaded = is_loaded




class CacheLoader(object):
    def __init__(self, callbackScheduler, vdm, cumulus_gateway):
        self.callbackScheduler = callbackScheduler
        self.vdm = vdm
        self.cumulus_gateway = cumulus_gateway
        self.lock_ = threading.RLock()
        self.vectorDataIDRequestCount_ = {}
        self.vectorDataIDToVectorSlices_ = {}
        self.vdm.setDropUnreferencedPagesWhenFull(True)

        self.cumulus_gateway.onCacheLoad = self.onCacheLoad

        self.ramCacheOffloadRecorder = CumulusNative.TrackingOfflineStorage(self.callbackScheduler)
        self.vdm.setOfflineCache(self.ramCacheOffloadRecorder)


    def is_unpaged_vector(self, vector_ivc):
        return (self.vdm.vectorDataIsLoaded(vector_ivc, 0, len(vector_ivc))
                and vector_ivc.isVectorEntirelyUnpaged())


    def extract_unpaged_vector(self, vector_ivc):
        #see if it's a string. This is the only way to be holding a Vector of char
        if vector_ivc.isVectorOfChar():
            res = self.vdm.extractVectorContentsAsNumpyArray(vector_ivc, 0, len(vector_ivc))
            assert res is not None
            return {'string': res.tostring()}

        #see if it's simple enough to transmit as numpy data
        if len(vector_ivc.getVectorElementsJOR()) == 1 and len(vector_ivc) > 1:
            res = self.vdm.extractVectorContentsAsNumpyArray(vector_ivc, 0, len(vector_ivc))

            if res is not None:
                assert len(res) == len(vector_ivc)
                firstElement = self.extractVectorItem(vector_ivc, 0)
                return {'firstElement': firstElement, 'contentsAsNumpyArrays': [res]}

        #see if we can extract the data as a regular pythonlist
        res = self.vdm.extractVectorContentsAsPythonArray(vector_ivc, 0, len(vector_ivc))
        assert res is not None
        return {'listContents': res}


    def extractVectorDataAsNumpyArray(self, vector_slice):
        return self.vdm.extractVectorContentsAsNumpyArray(
            vector_slice.vector,
            vector_slice.low_index,
            vector_slice.high_index
            )


    def vector_data_ids_for_slice(self, vector_slice):
        return vector_slice.vector.getVectorDataIdsForSlice(vector_slice.low_index,
                                                            vector_slice.high_index,
                                                            self.vdm)


    def extractVectorDataAsNumpyArrayInChunks(self, vector_slice, step_size=100000):
        """Return the data as a sequence of numpy arrays each of which is no larger than 'stepSize'.

        This is used to prevent us from creating memory fragmentation when we are loading
        lots of arrays of different sizes.
        """
        vector_data_ids = self.vector_data_ids_for_slice(vector_slice)
        if len(vector_data_ids) > 0 and not vector_slice.isLoaded:
            return None

        if not self.vectorDataIsLoaded(vector_slice):
            return None

        result = []
        index = vector_slice.low_index
        while index < vector_slice.high_index and result is not None:
            tail_result = self.extractVectorDataAsNumpyArray(
                VectorSlice(
                    vector_slice.vector,
                    index,
                    min(vector_slice.high_index, index+step_size)
                    )
                )
            index += step_size
            if tail_result is not None:
                result.append(tail_result)
            else:
                result = None

        if result is None and not self.vectorDataIsLoaded(vector_slice):
            logging.info("CumulusClient: %s was marked loaded but returned None", self)
            vector_slice.isLoaded = False
            self.reloadVector(vector_slice)

        return result


    def extractVectorItem(self, vector_ivc, index):
        return self.vdm.extractVectorItem(vector_ivc, index)


    def vectorDataIsLoaded(self, vector_slice):
        return self.vdm.vectorDataIsLoaded(
            vector_slice.vector,
            vector_slice.low_index,
            vector_slice.high_index
            )


    def setVectorLoadFlag_(self, vector_slice):
        is_loaded = self.computeVectorSliceIsLoaded_(vector_slice)
        vector_slice.set_is_loaded(is_loaded)


    def reloadVector(self, vector_slice):
        with self.lock_:
            self.setVectorLoadFlag_(vector_slice)

            for vector_data_id in self.vector_data_ids_for_slice(vector_slice):
                self.increaseVectorDataIdRequestCount_(vector_slice, vector_data_id)


    def increaseVectorDataIdRequestCount_(self, vector_slice, vector_data_id):
        #register our vector slice dependency
        if vector_data_id not in self.vectorDataIDToVectorSlices_:
            self.vectorDataIDToVectorSlices_[vector_data_id] = set()
        self.vectorDataIDToVectorSlices_[vector_data_id].add(vector_slice)

        if vector_data_id in self.vectorDataIDRequestCount_:
            self.vectorDataIDRequestCount_[vector_data_id] += 1
            return
        else:
            self.vectorDataIDRequestCount_[vector_data_id] = 1

        if not self.computeVectorDataIDIsLoaded_(vector_data_id):
            self.cumulus_gateway.requestCacheItem(vector_data_id)


    def get_vector_extractor(self, vector_ivc, callback):
        return lambda vector: self.extractVectorContents(vector, callback)


    def extractVectorContents(self, vector_ivc, callback):
        if len(vector_ivc) == 0:
            return {'listContents': []}

        #if this is an unpaged vector we can handle it without callback
        if self.is_unpaged_vector(vector_ivc):
            return self.extract_unpaged_vector(vector_ivc)

        res = None
        preventPythonArrayExtraction = False

        vec_slice = VectorSlice(vector_ivc, 0, vector_ivc.getVectorSize())
        #see if it's a string. This is the only way to be holding a Vector of char
        if vector_ivc.isVectorOfChar():
            res = self.extractVectorDataAsNumpyArray(vec_slice)
            if res is not None:
                res = {'string': res.tostring()}

        #see if it's simple enough to transmit as numpy data
        if res is None and len(vector_ivc.getVectorElementsJOR()) == 1 and len(vector_ivc) > 1:
            res = self.extractVectorDataAsNumpyArrayInChunks(vec_slice)
            if res is not None:
                firstElement = self.extractVectorItem(vector_ivc, 0)
                if firstElement is None:
                    #note we can't import this at the top of the file because this
                    # file gets imported during the build process,
                    # which doesn't have pyfora installed.
                    import pyfora.Exceptions as Exceptions
                    raise Exceptions.ForaToPythonConversionError((
                        "Shouldn't be possible to download data as numpy, and then not "
                        "get the first value"
                        ))

                res = {'firstElement': firstElement, 'contentsAsNumpyArrays': res}
            else:
                if not self.vectorDataIsLoaded(vec_slice):
                    #there's a race condition where the data could be loaded between now and
                    #the call to 'extractVectorDataAsPythonArray'. This prevents it.
                    preventPythonArrayExtraction = True

        #see if we can extract the data as a regular python list
        if not preventPythonArrayExtraction and res is None:
            res = self.extractVectorDataAsPythonArray(vec_slice)
            if res is not None:
                res = {'listContents': res}

        if res is None:
            def notify_callback(name, new_value, old_value):
                assert name == 'is_loaded'
                if new_value != old_value:
                    callback()

            vec_slice.observe('is_loaded', notify_callback)
            self.increaseVectorRequestCount(vec_slice)
            return None

        return res


    def onCacheLoad(self, vectorDataID):
        with self.lock_:
            vector_slices = self.vectorDataIDToVectorSlices_.get(vectorDataID, [])
            self.collectOffloadedVectors_()

            for vector_slice in vector_slices:
                vector_slice.set_is_loaded = self.computeVectorSliceIsLoaded_(vector_slice)


    def collectOffloadedVectors_(self):
        offloaded = self.ramCacheOffloadRecorder.extractDropped()

        if offloaded:
            logging.info("ComputedValue RamCache dropped %s", offloaded)

        for offloadedVecDataID in offloaded:
            for vector_slice in self.vectorDataIDToVectorSlices_.get(offloadedVecDataID, []):
                vector_slice.set_is_loaded(False)

        if offloaded:
            #check if there's anything we need to load
            self.sendReloadRequests()


    def sendReloadRequests(self):
        #TODO BUG brax: we don't know how to resubmit cacheload requests for unloaded items
        pass


    def extractVectorDataAsPythonArray(self, vector_slice):
        if vector_slice.vector is None:
            return None

        if len(self.vector_data_ids_for_slice(vector_slice)) > 0 and not vector_slice.is_loaded:
            return None

        return self.vdm.extractVectorContentsAsPythonArray(
            vector_slice.vector,
            vector_slice.low_index,
            vector_slice.high_index
            )


    def increaseVectorRequestCount(self, vector_slice):
        with self.lock_:
            self.setVectorLoadFlag_(vector_slice)

        for vector_data_id in self.vector_data_ids_for_slice(vector_slice):
            self.increaseVectorDataIdRequestCount_(vector_slice, vector_data_id)


    def computeVectorSliceIsLoaded_(self, vector_slice):
        return self.vdm.vectorDataIsLoaded(vector_slice.vector,
                                           vector_slice.low_index,
                                           vector_slice.high_index)


    def computeVectorDataIDIsLoaded_(self, vectorDataId):
        return self.vdm.vectorDataIdIsLoaded(vectorDataId)


    def decreaseVectorRequestCount(self, vector_slice):
        with self.lock_:
            self.setVectorLoadFlag_(vector_slice)

            for vector_data_id in self.vector_data_ids_for_slice(vector_slice):
                self.decreaseVectorDataIdRequestCount_(vector_slice, vector_data_id)


    def decreaseVectorDataIdRequestCount_(self, vector_slice, vector_data_id):
        assert vector_data_id in self.vectorDataIDRequestCount_

        self.vectorDataIDRequestCount_[vector_data_id] -= 1
        if self.vectorDataIDRequestCount_[vector_data_id] == 0:
            del self.vectorDataIDRequestCount_[vector_data_id]
            self.vectorDataIDToVectorSlices_[vector_data_id].discard(vector_slice)
            if not self.vectorDataIDToVectorSlices_[vector_data_id]:
                del self.vectorDataIDToVectorSlices_[vector_data_id]
