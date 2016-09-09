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

import logging
import threading
import time
import traceback
import os

import ufora.distributed.S3.S3Interface as S3Interface
import ufora.FORA.python.PythonIoTasks as PythonIoTasks
import ufora.util.OutOfProcessDownloader as OutOfProcessDownloader
import ufora.native.Cumulus as CumulusNative
import ufora.util.ManagedThread as ManagedThread
import ufora.config.Setup as Setup
import ufora.native.FORA as FORANative
import ufora.native.ImmutableTreeVector as NativeImmutableTreeVector

import ufora.FORA.python.PurePython.Converter as Converter
import ufora.FORA.python.PurePython.PyforaToJsonTransformer as PyforaToJsonTransformer
import ufora.FORA.python.ModuleDirectoryStructure as ModuleDirectoryStructure
import pyfora

class PythonIoTaskService(object):
    def __init__(self,
                 s3Interface,
                 objectStore,
                 vdm,
                 datasetRequestChannel,
                 threadCount=None,
                 maxObjectStoreAttempts=None,
                 objectStoreFailureIntervalSeconds=None):
        object.__init__(self)

        self.s3Interface = s3Interface
        self.objectStore = objectStore
        self.maxObjectStoreAttempts = Setup.config().objectStoreMaxAttempts \
            if maxObjectStoreAttempts is None \
            else max(1, maxObjectStoreAttempts)
        self.objectStoreFailureIntervalSeconds = Setup.config().objectStoreFailureIntervalSeconds \
            if objectStoreFailureIntervalSeconds is None \
            else objectStoreFailureIntervalSeconds
        self.objectStoreFailureCount = 0
        self.lastSuccessfulObjectStoreAttempt = 0.0
        self.vdm_ = vdm
        self.datasetRequestChannel_ = datasetRequestChannel
        self.threads_ = []
        self.teardown_ = False
        self.lock_ = threading.Lock()
        self.totalTasks = 0
        self.threadcount = threadCount or Setup.config().externalDatasetLoaderServiceThreads

        logging.debug(
            "OutOfProcessDownloader is %s",
            "out of process" if s3Interface.isCompatibleWithOutOfProcessDownloadPool else \
                "in memory"
            )

        self.outOfProcessDownloaderPool = \
            OutOfProcessDownloader.OutOfProcessDownloaderPool(
                self.threadcount,
                #for the inmemory tests, we can't run out of process because the fork may happen
                #before we populate the memory abstraction
                actuallyRunOutOfProcess=s3Interface.isCompatibleWithOutOfProcessDownloadPool
                )

    def loadLoop(self):
        logging.debug("Thread starting")

        while not self.teardown_:
            #serialize access to the channel
            request = self.datasetRequestChannel_.getTimeout(.1)

            if request is not None:
                logging.info("PythonIoTaskService loading %s", request)
                self.totalTasks += 1
                try:
                    self.processRequest(request)
                finally:
                    self.totalTasks -= 1

    def processRequest(self, request):
        try:
            if request.isLoadExternalDatasetIntoVector():
                self.handleLoadExternalDatasetRequest(
                    request.asLoadExternalDatasetIntoVector.toLoad,
                    request.guid
                    )
            elif request.isInitiateMultipartS3Upload():
                self.handleInitiateMultipartS3Upload(request)
            elif request.isCompleteMultipartS3Upload():
                self.handleCompleteMultipartS3Upload(request)
            elif request.isWriteMultipartS3UploadPart():
                self.handleWriteMultipartS3UploadPart(request)
            elif request.isCheckS3BucketSizeAndEtag():
                self.handleCheckS3BucketSizeAndEtag(request)
            elif request.isLoadExternalDatasetAsForaValue():
                self.handleLoadExternalDatasetAsForaValue(request)
            elif request.isPersistObject():
                self.handlePersistObject(request)
            elif request.isDeletePersistedObject():
                self.handleDeletePersistedObject(request)
            elif request.isExtractPersistedObject():
                self.handleExtractPersistedObject(request)
            elif request.isListPersistedObjects():
                self.handleListPersistedObjects(request)
            elif request.isOutOfProcessPythonCall():
                self.handleOutOfProcessPythonCall(request)
            else:
                raise UserWarning("Invalid request: %s" % request)

        except PythonIoTasks.UserCausedException as e:
            logging.error(
                "PythonIoTaskService caught user-caused exception handling %s: %s",
                request,
                e
                )
            self.datasetRequestChannel_.write(
                CumulusNative.PythonIoTaskResponse.UserCausedFailure(
                    request.guid,
                    str(e)  # No 'message' field on this object.
                    )
                )

        except PythonIoTasks.DatasetLoadException as e:
            logging.error(
                "PythonIoTaskService caught exception handling %s: %s",
                request,
                e)
            self.datasetRequestChannel_.write(
                CumulusNative.PythonIoTaskResponse.Failure(
                    request.guid,
                    str(e)  # No 'message' field on this object.
                    )
                )

        except S3Interface.S3InterfaceError as e:
            logging.error("PythonIoTaskService caught S3InterfaceError %s", e)

            if isinstance(e, (S3Interface.KeyNotFound, S3Interface.BucketNotFound)):
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.S3KeyDoesNotExist(
                        request.guid
                        )
                    )
            elif isinstance(e, (S3Interface.BucketAccessError, S3Interface.KeyAccessError)):
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.S3PermissionError(
                        request.guid
                        )
                    )
        except:
            logging.error(
                "PythonIoTaskService caught unknown exception: %s",
                traceback.format_exc()
                )

            self.datasetRequestChannel_.write(
                CumulusNative.PythonIoTaskResponse.Failure(
                    request.guid,
                    "Unknown python exception"
                    )
                )

    def handleInitiateMultipartS3Upload(self, request):
        uploadId = PythonIoTasks.initiateMultipartS3Upload(
            self.s3Interface,
            self.outOfProcessDownloaderPool,
            request.asInitiateMultipartS3Upload.credentials.bucketname,
            request.asInitiateMultipartS3Upload.credentials.keyname,
            request.asInitiateMultipartS3Upload.credentials.awsAccessKey,
            request.asInitiateMultipartS3Upload.credentials.awsSecretKey,
            request.asInitiateMultipartS3Upload.credentials.region
            )

        self.datasetRequestChannel_.write(
            CumulusNative.PythonIoTaskResponse.MultipartS3UploadInitiated(
                request.guid,
                uploadId
                )
            )

    def handleCompleteMultipartS3Upload(self, request):
        PythonIoTasks.completeMultipartS3Upload(
            self.s3Interface,
            self.outOfProcessDownloaderPool,
            request.asCompleteMultipartS3Upload.credentials.bucketname,
            request.asCompleteMultipartS3Upload.credentials.keyname,
            request.asCompleteMultipartS3Upload.credentials.awsAccessKey,
            request.asCompleteMultipartS3Upload.credentials.awsSecretKey,
            request.asCompleteMultipartS3Upload.credentials.region,
            request.asCompleteMultipartS3Upload.uploadId
            )

        self.datasetRequestChannel_.write(
            CumulusNative.PythonIoTaskResponse.Success(
                request.guid
                )
            )

    def handleWriteMultipartS3UploadPart(self, request):
        PythonIoTasks.writeMultipartS3UploadPart(
            self.s3Interface,
            self.outOfProcessDownloaderPool,
            request.asWriteMultipartS3UploadPart.credentials.bucketname,
            request.asWriteMultipartS3UploadPart.credentials.keyname,
            request.asWriteMultipartS3UploadPart.credentials.awsAccessKey,
            request.asWriteMultipartS3UploadPart.credentials.awsSecretKey,
            request.asWriteMultipartS3UploadPart.credentials.region,
            request.asWriteMultipartS3UploadPart.uploadId,
            request.asWriteMultipartS3UploadPart.part,
            request.asWriteMultipartS3UploadPart.objectData
            )

        self.datasetRequestChannel_.write(
            CumulusNative.PythonIoTaskResponse.Success(
                request.guid
                )
            )


    def handleLoadExternalDatasetAsForaValue(self, toRequest):
        externalDataset = toRequest.asLoadExternalDatasetAsForaValue.toLoad

        result = PythonIoTasks.loadExternalDatasetAsForaValue(
            externalDataset,
            self.vdm_
            )

        self.datasetRequestChannel_.write(
            CumulusNative.PythonIoTaskResponse.DatasetAsForaValue(
                toRequest.guid,
                result
                )
            )

    def handleCheckS3BucketSizeAndEtag(self, request):
        interface = self.s3Interface()

        try:
            if interface.bucketExists(request.asCheckS3BucketSizeAndEtag.bucketname) and \
               interface.keyExists(request.asCheckS3BucketSizeAndEtag.bucketname,
                                   request.asCheckS3BucketSizeAndEtag.keyname):
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.S3BucketSizeAndEtag(
                        request.guid,
                        "", #for now, we don't have a model for etags yet
                        interface.getKeySize(
                            request.asCheckS3BucketSizeAndEtag.bucketname,
                            request.asCheckS3BucketSizeAndEtag.keyname
                            )
                        )
                    )
            else:
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.S3KeyDoesNotExist(
                        request.guid
                        )
                    )
        except S3Interface.S3InterfaceError:
            self.datasetRequestChannel_.write(
                CumulusNative.PythonIoTaskResponse.S3PermissionError(
                    request.guid
                    )
                )

    def handleDeletePersistedObject(self, request):
        keyname = request.asDeletePersistedObject.objectPath

        while True:
            errorMessage = self.deletePersistedObject(keyname)
            if errorMessage is None:
                self.resetObjectStoreFailureCount()

                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.Success(
                        request.guid
                        )
                    )
                return

            logging.error(errorMessage)
            if self.isAtMaxObjectStoreFailures():
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.Failure(
                        request.guid,
                        errorMessage
                        )
                    )
                return


    def deletePersistedObject(self, keyname):
        try:
            PythonIoTasks.deletePersistedObject(keyname,
                                                self.objectStore,
                                                self.outOfProcessDownloaderPool)
        except:
            message = "Error deleting serialized object: %s:\n%s" % (
                keyname,
                traceback.format_exc()
                )

            #see if the object shows up as a listed object
            try:
                if len(self.objectStore.listValues(keyname)) == 0:
                    #if not, then we can consider the deletion a success
                    return
            except:
                message += "\n\nError while trying to list object:\n%s" % (
                    traceback.format_exc()
                    )
                return message

    def handleOutOfProcessPythonCall(self, request):
        #this should happen at bootup
        path = os.path.join(os.path.abspath(os.path.split(pyfora.__file__)[0]), "fora")
        moduleTree = ModuleDirectoryStructure.ModuleDirectoryStructure.read(path, "purePython", "fora")
        converter = Converter.constructConverter(moduleTree.toJson(), self.vdm_, stringDecoder=lambda s:s)

        transformer = PyforaToJsonTransformer.PyforaToJsonTransformer(stringEncoder=lambda s:s)

        assert self.vdm_ is not None

        anObjAsJson = converter.transformPyforaImplval(
            request.asOutOfProcessPythonCall.toCall,
            transformer,
            PyforaToJsonTransformer.ExtractVectorContents(self.vdm_)
            )

        result = PythonIoTasks.outOfProcessPythonCall(
            self.outOfProcessDownloaderPool,
            self.vdm_,
            anObjAsJson
            )

        self.datasetRequestChannel_.write(
            CumulusNative.PythonIoTaskResponse.OutOfProcessPythonCallResponse(
                request.guid,
                result
                )
            )

    def handleListPersistedObjects(self, request):
        while True:
            errorMessage, result = self.listPersistedObjects(request.asListPersistedObjects.objectPathPrefix)

            if errorMessage is None:
                self.resetObjectStoreFailureCount()
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.ObjectPaths(
                        request.guid,
                        NativeImmutableTreeVector.ImmutableTreeVectorOfString(result)
                        )
                    )
                return

            logging.error(errorMessage)
            if self.isAtMaxObjectStoreFailures():
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.Failure(
                        request.guid,
                        errorMessage
                        )
                    )
                return

    def handleExtractPersistedObject(self, request):
        keyname = request.asExtractPersistedObject.objectPath

        while True:
            errorMessage, result = self.extractPersistedObject(keyname)
            if errorMessage is None:
                self.resetObjectStoreFailureCount()
                if result is None:
                    # keyname does not exist
                    self.datasetRequestChannel_.write(
                        CumulusNative.PythonIoTaskResponse.ObjectDoesNotExist(
                            request.guid
                            )
                        )
                else:
                    self.datasetRequestChannel_.write(
                        CumulusNative.PythonIoTaskResponse.ObjectExtracted(
                            request.guid,
                            FORANative.NoncontiguousByteBlock(result)
                            )
                        )
                return

            logging.error(errorMessage)
            if self.isAtMaxObjectStoreFailures():
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.Failure(
                        request.guid,
                        errorMessage
                        )
                    )
                return


    def extractPersistedObject(self, keyname):
        try:
            result = PythonIoTasks.extractPersistedObject(keyname,
                                                          self.objectStore,
                                                          self.outOfProcessDownloaderPool)
            return None, result
        except:
            message = "Error reading serialized object: %s:\n%s" % (
                keyname,
                traceback.format_exc()
                )

            #see if the object shows up as a listed object
            try:
                if len(self.objectStore.listValues(keyname)) == 0:
                    return None, None
            except:
                message += "\n\nError while trying to list serialized object:\n%s" % (
                    traceback.format_exc()
                    )

            return message, None

    def listPersistedObjects(self, prefix):
        try:
            result = PythonIoTasks.listPersistedObjects(prefix,
                                                          self.objectStore,
                                                          self.outOfProcessDownloaderPool)
            return None, result
        except:
            message = "Error listing persisted objects: %s:\n%s" % (
                prefix,
                traceback.format_exc()
                )

            return message, None



    def handlePersistObject(self, request):
        while True:
            errorMessage, dataLen = self.writeToObjectStore(request.asPersistObject)
            if errorMessage is None:
                self.resetObjectStoreFailureCount()
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.DataSuccessfullyPersisted(
                        request.guid,
                        dataLen
                        )
                    )
                return

            logging.error(errorMessage)
            if self.isAtMaxObjectStoreFailures():
                self.datasetRequestChannel_.write(
                    CumulusNative.PythonIoTaskResponse.Failure(
                        request.guid,
                        errorMessage
                        )
                    )
                return

    def writeToObjectStore(self, persistObjectRequest):
        try:
            dataSize = PythonIoTasks.persistObject(persistObjectRequest,
                                                   self.objectStore,
                                                   self.outOfProcessDownloaderPool)
            return None, dataSize
        except:
            message = "Error writing serialized object: %s:\n%s" % (
                persistObjectRequest.objectPath,
                traceback.format_exc()
                )
            return message, None


    def isAtMaxObjectStoreFailures(self):
        with self.lock_:
            self.objectStoreFailureCount += 1
            if self.objectStoreFailureCount >= self.maxObjectStoreAttempts and \
                    self.lastSuccessfulObjectStoreAttempt + self.objectStoreFailureIntervalSeconds < time.time():
                return True
        # add some delay before retrying
        time.sleep(0.2)
        return False

    def resetObjectStoreFailureCount(self):
        with self.lock_:
            self.objectStoreFailureCount = 0
            self.lastSuccessfulObjectStoreAttempt = time.time()


    def handleLoadExternalDatasetRequest(self, request, guid):
        t0 = time.time()

        PythonIoTasks.loadExternalDataset(
            self.s3Interface,
            request,
            self.vdm_,
            self.outOfProcessDownloaderPool
            )

        logging.info(
            "PythonIoTaskService succeeded in loading %s in %s. tasks=%s",
            request,
            time.time() - t0,
            self.totalTasks
            )

        self.datasetRequestChannel_.write(
            CumulusNative.PythonIoTaskResponse.Success(
                guid
                )
            )

    def stopService(self):
        self.teardown()

    def startService(self):
        with self.lock_:
            if self.threads_:
                return

            logging.debug(
                "Starting %s PythonIoTasks service threads",
                Setup.config().externalDatasetLoaderServiceThreads
                )

            for ix in range(self.threadcount):
                self.threads_.append(
                    ManagedThread.ManagedThread(
                        target=self.loadLoop
                        )
                    )
                self.threads_[-1].start()

    def teardown(self):
        with self.lock_:
            if self.teardown_:
                return
            self.teardown_ = True

        for thread in self.threads_:
            thread.join()

        self.outOfProcessDownloaderPool.teardown()

        with self.lock_:
            self.threads_ = []
            self.s3Interface = None
            self.vdm_ = None
            self.datasetRequestChannel_ = None
            self.outOfProcessDownloaderPool = None


