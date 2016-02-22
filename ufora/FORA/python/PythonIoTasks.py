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

import ufora.distributed.S3.S3Interface as S3Interface
import ufora.distributed.util.common as common
import ufora.native.FORA as ForaNative
import ufora.native.Cumulus as CumulusNative
import ufora.config.Setup as Setup
import ufora.util.ExponentialMovingAverage as ExponentialMovingAverage
import logging
import os
import requests
try:
    import pyodbc
except ImportError:
    import pypyodbc as pyodbc
import json
import time
import threading
import traceback
import sys

class UserCausedException(Exception):
    """Represents a Python failure caused by bad user code,
       like a malformed ODBC connection string."""
    pass

class DatasetLoadException(Exception):
    pass

class InvalidDatasetException(Exception):
    pass

class ObjectStoreException(Exception):
    pass


def loadExternalDataset(s3InterfaceFactory, vdid, vdm, outOfProcessDownloaderPool):
    if not vdid.isExternal():
        raise DatasetLoadException("Not an external VDID")

    datasetDescriptor = vdid.asExternal.dataset

    if datasetDescriptor.isS3DatasetSlice():
        loadS3DatasetSlice(datasetDescriptor,
                           s3InterfaceFactory,
                           vdid,
                           vdm,
                           outOfProcessDownloaderPool)
    elif datasetDescriptor.isEntireS3Dataset():
        loadEntireS3Dataset(datasetDescriptor, s3InterfaceFactory, vdid, vdm)
    elif datasetDescriptor.isHttpRequestDataset():
        loadHttpDataset(datasetDescriptor, vdid, vdm)
    elif datasetDescriptor.isOdbcRequestDataset():
        loadOdbcDataset(datasetDescriptor, vdid, vdm)
    elif datasetDescriptor.isEntireFileDataset():
        loadEntireFileDataset(datasetDescriptor, vdid, vdm)
    elif datasetDescriptor.isFileSliceDataset():
        loadFileSliceDataset(datasetDescriptor, vdid, vdm)
    else:
        raise DatasetLoadException("Unknown dataset type: %s" % datasetDescriptor)


def loadExternalDatasetAsForaValue(datasetDescriptor, vdm):
    if datasetDescriptor.isTestDataset():
        return normalComputationResult(ForaNative.ImplValContainer(time.time()))
    elif datasetDescriptor.isExceptionThrowingDataset():
        return ForaNative.ComputationResult.Exception(
            ForaNative.ImplValContainer("ExceptionThrowingDataset"),
            ForaNative.ImplValContainer()
            )
    elif datasetDescriptor.isFailureInducingDataset():
        raise DatasetLoadException("FailureInducingDataset")
    elif datasetDescriptor.isHttpRequestDataset():
        t0 = time.time()

        data, statusCode = loadHttpRequestDataset(datasetDescriptor.asHttpRequestDataset.dataset)

        logging.info("Took %s to get %s bytes from loadHttpRequestDataset",
                     time.time() - t0,
                     len(data))

        return normalComputationResult(
            ForaNative.CreateNamedTuple(
                (
                    vdm.loadByteArrayIntoNewVector(data),
                    ForaNative.ImplValContainer(int(statusCode))
                ),
                ("result", "status")
                )
            )
    elif datasetDescriptor.isOdbcRequestDataset():
        try:
            logging.info("Attempting to initialize an ODBC request.")
            data = loadOdbcRequestDataset(datasetDescriptor.asOdbcRequestDataset.dataset, vdm)
            return normalComputationResult(data)
        except Exception as e:
            raise UserCausedException("ODBC request failed: %s" % e.message)
    else:
        raise DatasetLoadException("Can't handle dataset %s" % datasetDescriptor)


def persistObject(obj, objectStore, outOfProcessDownloaderPool):
    key = obj.objectPath
    objectStoreUploader = ObjectStoreUploader(objectStore, key)

    def outputCallback(response):
        if response != "OK":
            raise ObjectStoreException("Can't write to key: " + key)

    dataLen = [None]
    def inputCallback(fd):
        data = obj.objectData.toString()
        dataLen[0] = len(data)
        os.write(fd, common.prependSize(data))

    outOfProcessDownloaderPool.getDownloader() \
            .executeAndCallbackWithString(objectStoreUploader,
                                          outputCallback,
                                          inputCallback)
    return dataLen[0]

def extractPersistedObject(key, objectStore, outOfProcessDownloaderPool):
    objectStoreDownloader = ObjectStoreDownloader(objectStore, key)

    result = [None]
    def callback(loadedData):
        result[0] = loadedData

    outOfProcessDownloaderPool.getDownloader() \
        .executeAndCallbackWithString(objectStoreDownloader, callback)
    return result[0]

def listPersistedObjects(prefix, objectStore, outOfProcessDownloaderPool):
    objectStoreLister = ObjectStoreLister(objectStore, prefix)

    result = [None]
    def callback(loadedData):
        #the string will contain a jsonified list of strings
        result[0] = [str(x) for x in json.loads(loadedData)]

    outOfProcessDownloaderPool.getDownloader() \
        .executeAndCallbackWithString(objectStoreLister, callback)
    return result[0]


def deletePersistedObject(key, objectStore, outOfProcessDownloaderPool):
    objectStoreDeleter = ObjectStoreDeleter(objectStore, key)

    def outputCallback(response):
        if response != "OK":
            raise ObjectStoreException("Can't delete key: " + key)

    outOfProcessDownloaderPool.getDownloader() \
            .executeAndCallbackWithString(objectStoreDeleter,
                                          outputCallback)

class S3MultipartUploadInitiator(object):
    def __init__(self, s3Interface, bucketname, keyname):
        self.s3Interface = s3Interface
        self.bucketname = bucketname
        self.keyname = keyname

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "S3MultipartUploadInitiator(bucketname=%s,keyname=%s)" % (
            self.bucketname,
            self.keyname
            )

    def __call__(self):
        return self.s3Interface.initiateMultipartUpload(self.bucketname, self.keyname)

class S3MultipartUploadCompleter(object):
    def __init__(self, s3Interface, bucketname, keyname, uploadId):
        self.s3Interface = s3Interface
        self.bucketname = bucketname
        self.keyname = keyname
        self.uploadId = uploadId

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "S3MultipartUploadCompleter(bucketname=%s,keyname=%s,uploadId=%s)" % (
            self.bucketname,
            self.keyname,
            self.uploadId
            )

    def __call__(self):
        self.s3Interface.completeMultipartUpload(self.bucketname, self.keyname, self.uploadId)
        return "OK"

class S3MultipartUploadWriter(object):
    def __init__(self,
                 s3Interface,
                 bucketname,
                 keyname,
                 uploadId,
                 partNumber
                 ):
        self.s3Interface = s3Interface
        self.bucketname = bucketname
        self.keyname = keyname
        self.uploadId = uploadId
        self.partNumber = partNumber

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "S3MultipartUploadWriter(bucketname=%s,keyname=%s,uploadId=%s, partNumber=%s)" % (
            self.bucketname,
            self.keyname,
            self.uploadId,
            self.partNumber
            )

    def __call__(self, dataAsString):
        self.s3Interface.setMultipartUploadPart(
            self.bucketname,
            self.keyname,
            self.uploadId,
            self.partNumber,
            dataAsString
            )
        return "OK"

def initiateMultipartS3Upload(s3InterfaceFactory,
                              outOfProcessDownloaderPool,
                              bucketname,
                              keyname,
                              awsAccessKey,
                              awsSecretKey,
                              region):
    initiator = S3MultipartUploadInitiator(
        s3InterfaceFactory(awsAccessKey, awsSecretKey),
        bucketname,
        keyname
        )

    uploadId = []
    def outputCallback(response):
        uploadId.append(response)

    outOfProcessDownloaderPool.getDownloader() \
            .executeAndCallbackWithString(initiator,
                                          outputCallback)

    return uploadId[0]

def completeMultipartS3Upload(s3InterfaceFactory,
                              outOfProcessDownloaderPool,
                              bucketname,
                              keyname,
                              awsAccessKey,
                              awsSecretKey,
                              region,
                              uploadId):
    completer = S3MultipartUploadCompleter(
        s3InterfaceFactory(awsAccessKey, awsSecretKey),
        bucketname,
        keyname,
        uploadId
        )

    def outputCallback(response):
        if response != "OK":
            raise UserWarning("Couldn't finish upload")

    outOfProcessDownloaderPool.getDownloader() \
            .executeAndCallbackWithString(completer,
                                          outputCallback)

def writeMultipartS3UploadPart(s3InterfaceFactory,
                               outOfProcessDownloaderPool,
                               bucketname,
                               keyname,
                               awsAccessKey,
                               awsSecretKey,
                               region,
                               uploadId,
                               partNumber,
                               dataAsNBB):
    writer = S3MultipartUploadWriter(
        s3InterfaceFactory(awsAccessKey, awsSecretKey),
        bucketname,
        keyname,
        uploadId,
        partNumber
        )

    def outputCallback(response):
        if response != "OK":
            raise UserWarning("Couldn't finish upload")

    def inputCallback(fd):
        data = dataAsNBB.toString()
        os.write(fd, common.prependSize(data))

    outOfProcessDownloaderPool.getDownloader() \
            .executeAndCallbackWithString(writer, outputCallback, inputCallback)

def loadS3DatasetSlice(datasetDescriptor,
                       s3InterfaceFactory,
                       vdid,
                       vdm,
                       outOfProcessDownloaderPool):
    def callback(fd, bytesToLoad):
        if not vdm.loadByteArrayIntoExternalDatasetPageFromFileDescriptor(vdid, fd, bytesToLoad):
            raise DatasetLoadException("Couldn't load dataset into VDM")

    loadS3Dataset(
        s3InterfaceFactory,
        datasetDescriptor.asS3DatasetSlice.dataset,
        datasetDescriptor.asS3DatasetSlice.lowOffset,
        datasetDescriptor.asS3DatasetSlice.highOffset,
        outOfProcessDownloaderPool,
        callback
        )


def loadEntireS3Dataset(datasetDescriptor, s3InterfaceFactory, vdid, vdm):
    try:
        vectorSlices = produceVDIDSlicesForEntireS3Dataset(
            s3InterfaceFactory,
            datasetDescriptor.asEntireS3Dataset.dataset,
            vdm
            )

        vector = ForaNative.createFORAFreeBinaryVectorFromSlices(vectorSlices, vdm)

        if not vdm.loadImplvalIntoUnloadedVectorHandle(vdid, vector):
            raise DatasetLoadException("Couldn't load dataset into VDM")
    except InvalidDatasetException as e:
        if not vdm.loadImplvalIntoUnloadedVectorHandle(
                vdid,
                ForaNative.ImplValContainer(e.message)):
            raise DatasetLoadException("Couldn't load dataset into VDM")
    except:
        logging.error("WTF: %s", traceback.format_exc())


def loadEntireFileDataset(datasetDescriptor, vdid, vdm):
    try:
        vectorSlices = produceVDIDSlicesForFile(
            datasetDescriptor.asEntireFileDataset.file
            )
        vector = ForaNative.createFORAFreeBinaryVectorFromSlices(vectorSlices, vdm)
        if not vdm.loadImplvalIntoUnloadedVectorHandle(vdid, vector):
            raise DatasetLoadException("Couldn't load dataset into VDM")

    except InvalidDatasetException as e:
        logging.error("Failed to load dataset: %s", e.message)
        if not vdm.loadImplvalIntoUnloadedVectorHandle(
                vdid,
                ForaNative.ImplValContainer(e.message)):
            raise DatasetLoadException("Couldn't load dataset into VDM")


def loadFileSliceDataset(datasetDescriptor, vdid, vdm):
    fd = None
    path = datasetDescriptor.asFileSliceDataset.file.path
    lowIndex = datasetDescriptor.asFileSliceDataset.lowOffset
    highIndex = datasetDescriptor.asFileSliceDataset.highOffset

    try:
        fd = os.open(path, os.O_RDONLY)
        os.lseek(fd, lowIndex, os.SEEK_SET)
        if not vdm.loadByteArrayIntoExternalDatasetPageFromFileDescriptor(
                vdid,
                fd,
                highIndex - lowIndex):
            raise DatasetLoadException("Coulnd't load file slice into VDM")
    except os.error as e:
        message = 'Error loading file slice dataset: %s, %d-%d:\n%s' % (
            path,
            lowIndex,
            highIndex,
            e)
        logging.error(message)
        raise DatasetLoadException(message)
    finally:
        if fd is not None:
            os.close(fd)

def loadHttpDataset(datasetDescriptor, vdid, vdm):
    try:
        data, statusCode = loadHttpRequestDataset(
            datasetDescriptor.asHttpRequestDataset.dataset
            )
        if statusCode != 200:
            raise InvalidDatasetException(
                "Load returned status code %s" % statusCode
                )

        if not vdm.loadByteArrayIntoExternalDatasetPageAsVector(vdid, data):
            raise DatasetLoadException("Couldn't load dataset into VDM")
    except InvalidDatasetException as e:
        if not vdm.loadImplvalIntoUnloadedVectorHandle(
                vdid,
                ForaNative.ImplValContainer(e.message)):
            raise DatasetLoadException("Couldn't load dataset into VDM")


def loadOdbcDataset(datasetDescriptor, vdid, vdm):
    try:
        implval = loadOdbcRequestDataset(datasetDescriptor.asOdbcRequestDataset.dataset,
                                         vdm)

        if not vdm.loadImplvalIntoUnloadedVectorHandle(vdid, implval):
            raise DatasetLoadException("Couldn't load dataset into VDM")

    except UserCausedException as e:
        if not vdm.loadImplvalIntoUnloadedVectorHandle(
                vdid,
                ForaNative.ImplValContainer(e.message)):
            raise DatasetLoadException("Couldn't load dataset into VDM")

        # Propagate this exception to the handler even if the loading was correct.
        raise e

    except InvalidDatasetException as e:
        if not vdm.loadImplvalIntoUnloadedVectorHandle(
                vdid,
                ForaNative.ImplValContainer(e.message)):
            raise DatasetLoadException("Couldn't load dataset into VDM")




downloadThroughputEMA = ExponentialMovingAverage.ExponentialMovingAverage(20.0)

def loadS3Dataset(s3InterfaceFactory,
                  dataset,
                  lowOffset,
                  highOffset,
                  outOfProcessDownloaderPool,
                  callback):
    """Attempt to load an s3 dataset. Returns (bytes, count), or None if unsuccessful."""
    s3Interface, bucketname, keyname = parseS3Dataset(s3InterfaceFactory, dataset)

    dataDownloader = S3KeyDownloader(s3Interface, bucketname, keyname, lowOffset, highOffset)

    t0 = time.time()

    outOfProcessDownloaderPool.getDownloader() \
            .executeAndCallbackWithFileDescriptor(dataDownloader, callback)

    downloadThroughputEMA.observe(
        (highOffset - lowOffset) / 1024 / 1024.0 / (time.time() - t0),
        time.time() - t0
        )

    logging.info("EMA: %s", downloadThroughputEMA.currentRate())


def parseS3Dataset(s3InterfaceFactory, s3Dataset):
    """Log in to amazon S3 and return an appropriate s3Interface and a bucket/keypair"""
    if s3Dataset.isInternal():
        #use the internal login. This should have access only to our one internal bucket
        return (
            s3InterfaceFactory(),
            Setup.config().userDataS3Bucket,
            s3Dataset.asInternal.keyname
            )

    elif s3Dataset.isExternal():
        asE = s3Dataset.asExternal
        interface = s3InterfaceFactory()

        return (interface, asE.bucket, asE.key)
    else:
        raise DatasetLoadException("Unknown dataset type")


def produceVDIDSlicesForEntireS3Dataset(s3InterfaceFactory, s3Dataset, vdm):
    s3Interface, bucketname, keyPrefix = parseS3Dataset(s3InterfaceFactory, s3Dataset)

    if s3Interface.bucketExists(bucketname) and s3Interface.keyExists(bucketname, keyPrefix):
        return produceVDIDSlicesForSingleBucketKeyPair(s3Interface,
                                                       bucketname,
                                                       keyPrefix,
                                                       s3Dataset)
    else:
        if not s3Interface.bucketExists(bucketname):
            logging.info("Can't load dataset. Bucket '%s' doesn't exist.", bucketname)
            raise InvalidDatasetException("No bucket matching '%s'" % str(bucketname))

        keysAndSizesMatching = s3Interface.listKeysWithPrefix(bucketname, keyPrefix + "_")

        indicesKeysAndSizes = []

        for key, size, mtime in keysAndSizesMatching:
            try:
                index = int(key[len(keyPrefix)+1:])
                indicesKeysAndSizes.append((index, key, size))
            except ValueError:
                pass

        keysAndSizesMatching = [(key, size) for _, key, size in sorted(indicesKeysAndSizes)]

    if not keysAndSizesMatching:
        raise InvalidDatasetException(
            "No keys matching %s/%s in %s" % (bucketname, keyPrefix, s3Interface)
            )

    slices = []

    for key, _ in keysAndSizesMatching:
        slices.extend(
            produceVDIDSlicesForSingleBucketKeyPair(s3Interface, bucketname, key, s3Dataset)
            )

    return slices


CHUNK_SIZE = 50 * 1024 * 1024
def produceVDIDSlicesForSingleBucketKeyPair(s3Interface, bucketname, keyname, s3Dataset):
    try:
        totalBytes = s3Interface.getKeySize(bucketname, keyname)

        chunks = getAppropriateChunksForSize(totalBytes, CHUNK_SIZE)

        slices = []

        for lowIndex, highIndex in chunks:
            externalDatasetDesc = ForaNative.ExternalDatasetDescriptor.S3DatasetSlice(
                s3DatasetWithKeyname(s3Dataset, keyname),
                lowIndex,
                highIndex
                )

            vectorDataId = ForaNative.VectorDataID.External(externalDatasetDesc)

            vectorDataIdSlice = ForaNative.createVectorDataIDSlice(vectorDataId,
                                                                   0,
                                                                   highIndex - lowIndex)

            slices.append(vectorDataIdSlice)

        return slices

    except S3Interface.S3InterfaceError as e:
        message = "Error loading S3 dataset: %s/%s:\n%s" % (
            bucketname,
            keyname,
            e
            )
        logging.error(message)
        raise InvalidDatasetException(message)


def produceVDIDSlicesForFile(fileDataset):
    try:
        logging.error("Getting file size: %s", fileDataset.path)
        totalBytes = os.path.getsize(fileDataset.path)
        chunks = getAppropriateChunksForSize(totalBytes, CHUNK_SIZE)

        slices = []
        for lowIndex, highIndex in chunks:
            datasetDescriptor = ForaNative.ExternalDatasetDescriptor.FileSliceDataset(
                fileDataset,
                lowIndex,
                highIndex
                )
            vectorDataId = ForaNative.VectorDataID.External(datasetDescriptor)
            vectorDataIdSlice = ForaNative.createVectorDataIDSlice(vectorDataId,
                                                                   0,
                                                                   highIndex - lowIndex)
            slices.append(vectorDataIdSlice)
        return slices
    except os.error as e:
        message = 'Error loading file dataset: %s:\n%s' % (fileDataset.path, e)
        logging.error(message)
        raise DatasetLoadException(message)


def getAppropriateChunksForSize(size, chunkSize):
    chunks = []
    curIx = 0

    while curIx < size:
        top = min(curIx + chunkSize, size)
        chunks.append((curIx, top))
        curIx = top

    if len(chunks) > 1 and (chunks[-1][1] - chunks[-1][0]) < chunkSize / 2:
        newLow = chunks[-2][0]
        newHigh = chunks[-1][1]

        chunks[-2:] = [(newLow, newHigh)]

    return chunks


def s3DatasetWithKeyname(s3Dataset, keyname):
    if s3Dataset.isExternal():
        return ForaNative.S3Dataset.External(
            s3Dataset.asExternal.bucket,
            keyname,
            s3Dataset.asExternal.awsAccessKey,
            s3Dataset.asExternal.awsSecretKey,
            ""
            )
    else:
        return ForaNative.S3Dataset.Internal(keyname)


def extractColumnDataFromQueryCursor(cursor):
    columns = []
    names = []

    for row in cursor:
        if len(names) == 0:
            names = tuple((x[0] for x in row.cursor_description))
            columns = [[] for _ in names]

        for columnIx in range(len(row)):
            columns[columnIx].append(processColumnValue(row[columnIx]))

    return columns, names


def processColumnValue(val):
    if isinstance(val, unicode):
        return val.encode("ascii", "ignore")

    return val


def loadOdbcRequestDataset(request, vdm):
    try:
        logging.info("Initializing a connection.")
        connection = pyodbc.connect(request.connectionString)
    except Exception as e:
        raise UserCausedException("Failed to connect: %s" % e)

    cursor = connection.cursor()

    # Attempt the query.
    queries = request.query
    for query in queries:
        try:
            logging.info("Executing query: %s", query)
            cursor = cursor.execute(query)
        except Exception as e:
            logging.error("Query \"%s\" failed. Closing connection.", query)
            connection.close()
            raise UserCausedException("ODBC query failed: %s | Message: %s" % (query, e))

    columns, names = convertListOfTuplesToTupleOfVectors(cursor, vdm)
    tr = ForaNative.CreateNamedTuple(tuple(columns), names)

    connection.close()

    return tr


def convertListOfTuplesToTupleOfVectors(cursor, vdm):
    #this should really be done using unixODBC's C Api. This implementation will work,
    #but isn't smart enough to page the columns as we build them, and also has boost-python-barrier
    #slowness

    columns, names = extractColumnDataFromQueryCursor(cursor)

    columns = [listToForaVector(x, vdm) for x in columns]

    return columns, tuple(names)


def listToForaVector(elements, vdm):
    return ForaNative.simpleListToVector(elements, vdm)


def loadHttpRequestDataset(httpRequest):
    """Download data from 'httpRequest' (a C++ HttpRequest object) and return the byte content."""
    try:
        result = requests.get(httpRequest.url)
    except requests.exceptions.InvalidURL:
        raise InvalidDatasetException("Invalid url: %s" % httpRequest.url)
    except requests.exceptions.MissingSchema:
        raise InvalidDatasetException("Invalid url: %s" % httpRequest.url)
    except requests.exceptions.TooManyRedirects:
        raise InvalidDatasetException("Too many redirects")
    except requests.exceptions.Timeout:
        raise InvalidDatasetException("Server timed out")
    except requests.exceptions.ConnectionError:
        raise InvalidDatasetException("Couldn't connect to url %s" % httpRequest.url)
    except requests.exceptions.RequestException as e:
        raise InvalidDatasetException(e.message)

    return str(result.content), result.status_code

def normalComputationResult(result):
    return ForaNative.ComputationResult.Result(
        result,
        ForaNative.ImplValContainer()
        )


class S3KeyDownloader(object):
    def __init__(self, s3Interface, bucketname, keyname, lowOffset, highOffset):
        self.s3Interface = s3Interface
        self.bucketname = bucketname
        self.keyname = keyname
        self.lowOffset = lowOffset
        self.highOffset = highOffset

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "S3KeyDownloader(bucketname=%s,keyname=%s,range=(%s,%s),interface=%s)" % (
            self.bucketname,
            self.keyname,
            self.lowOffset,
            self.highOffset,
            self.s3Interface
            )

    def __call__(self):
        start, stop = self.lowOffset, self.highOffset

        logging.info("Starting extraction of %s, %s, [%s, %s]",
                     self.bucketname,
                     self.keyname,
                     start,
                     stop)

        t0 = time.time()

        totalThreads = Setup.config().externalDatasetLoaderThreadcount

        def downloadThread(ix):
            def downloader():
                low = start + (stop - start) * ix / totalThreads
                high = start + (stop - start) * (ix + 1) / totalThreads

                tries = 0
                while True:
                    try:
                        results[ix] = self.s3Interface.getKeyValueOverRange(
                            self.bucketname,
                            self.keyname,
                            low,
                            high
                            )
                        return
                    except:
                        if tries < 10:
                            logging.warn(
                                "Task %s had an exception:%s\nTries = %s. We will fail the " +
                                "request when 'tries' gets to 10",
                                self,
                                traceback.format_exc(),
                                tries
                                )
                            tries += 1
                        else:
                            results[ix] = sys.exc_info()
                            return

            return downloader


        results = []
        threads = []
        for ix in range(totalThreads):
            results.append(None)
            threads.append(
                threading.Thread(target=downloadThread(ix))
                )

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        for r in results:
            if isinstance(r, tuple):
                exc_info = r
                raise exc_info[0], exc_info[1], exc_info[2]

        result = "".join(results)

        assert len(result) == stop - start

        logging.info("Actually extracting %s from s3 took %s",
                     len(result) / 1024 / 1024.0,
                     time.time() - t0)

        return result


class ObjectStoreUploader(object):
    def __init__(self, object_store, key):
        self.object_store = object_store
        self.key = key

    def __repr__(self):
        return "ObjectStoreUploader(object_store=%s, key=%s)" % (
            type(self.object_store),
            self.key
            )

    def __str__(self):
        return repr(self)

    def __call__(self, data):
        self.object_store.writeValue(self.key, data)
        return "OK"

class ObjectStoreDownloader(object):
    def __init__(self, object_store, key):
        self.object_store = object_store
        self.key = key

    def __repr__(self):
        return "ObjectStoreDownloader(object_store=%s, key=%s)" % (
            type(self.object_store),
            self.key
            )

    def __str__(self):
        return repr(self)

    def __call__(self):
        return self.object_store.readValue(self.key)

class ObjectStoreLister(object):
    def __init__(self, object_store, prefix):
        self.object_store = object_store
        self.prefix = prefix

    def __repr__(self):
        return "ObjectStoreLister(object_store=%s, prefix=%s)" % (
            type(self.object_store),
            self.prefix
            )

    def __str__(self):
        return repr(self)

    def __call__(self):
        return json.dumps([x[0] for x in self.object_store.listValues(self.prefix)])


class ObjectStoreDeleter(object):
    def __init__(self, object_store, key):
        self.object_store = object_store
        self.key = key

    def __repr__(self):
        return "ObjectStoreDeleter(object_store=%s, key=%s)" % (
            type(self.object_store),
            self.key
            )

    def __str__(self):
        return repr(self)

    def __call__(self):
        self.object_store.deleteValue(self.key)
        return "OK"






