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
import collections
import logging
import threading
import time

InMemoryS3Key = collections.namedtuple('InMemoryS3Key', ['value', 'mtime'])

class InMemoryS3State(object):

    def __init__(self):
        self.writeFailureInjector = None
        self.delayAfterWriteFunction = None
        self.throughput = None
        self.clear()

    def clear(self):
        self.buckets_ = {}
        self.bucketOwners_ = {}
        self.lock = threading.RLock()

        self.throughput = None

        self.bytesLoadedPerMachine = {}

    def logBytesLoadedAndDelay(self, machine, data):
        with self.lock:
            if machine not in self.bytesLoadedPerMachine:
                self.bytesLoadedPerMachine[machine] = 0
            self.bytesLoadedPerMachine[machine] += data

        if self.throughput is not None:
            time.sleep(float(data) / self.throughput)

    def setThroughputPerMachine(self, throughput):
        self.throughput = throughput

    def createBucket(self, bucketName, credentials):
        assert bucketName not in self.bucketOwners_
        self.bucketOwners_[bucketName] = credentials
        self.buckets_[bucketName] = {}

    def validateAccess(self, bucketName, credentials):
        owner = self.bucketOwners_.get(bucketName)
        if owner is None:
            raise S3Interface.BucketNotFound(bucketName)

        if credentials != owner and owner != S3Interface.S3Interface.publicCredentials:
            # the owner (None, None) indicates a publicly accessible bucket
            logging.error("Access Denies: owner=%s, credentials=%s",
                          owner, credentials)
            raise S3Interface.BucketAccessError(bucketName)

    def listBuckets(self, credentials):
        return [
            name for name, owner in self.bucketOwners_.iteritems()
            if owner == credentials or owner == self.publicCredentials
            ]

class InMemoryS3InterfaceFactory(S3Interface.S3InterfaceFactory):
    isCompatibleWithOutOfProcessDownloadPool = False

    def __init__(self, state=None, onMachine=None):
        self.state_ = state or InMemoryS3State()
        self.machine_ = onMachine

    def setWriteFailureInjector(self, injector):
        """Cause the system to call a function to determine whether writes succeed.

        injector: function from (bucketname,key) -> True indicating whether to inject a fault.
        """
        self.state_.writeFailureInjector = injector

    def setDelayAfterWriteInjector(self, injector):
        """Cause the system to call a function to determine whether to delay writes.

        injector: function from (bucketname,key) -> seconds indicating whether to
            wait after posting the read. The store will be unlocked, but clients will
            be blocked.
        """
        self.state_.delayAfterWriteFunction = injector

    def clearState(self):
        self.state_.clear()

    def withMachine(self, machine):
        return InMemoryS3InterfaceFactory(self.state_, machine)

    def setThroughputPerMachine(self, bytesPerSecond):
        self.state_.setThroughputPerMachine(bytesPerSecond)

    def getPerMachineBytecounts(self):
        return dict(self.state_.bytesLoadedPerMachine)

    def totalBytesInStorage(self):
        total = 0

        for bucket in self.state_.buckets_:
            for key in self.state_.buckets_[bucket]:
                total += len(self.state_.buckets_[bucket][key].value)

        return total

    def listAllBucketKeyPairs(self):
        res = []
        for bucket in self.state_.buckets_:
            for key in self.state_.buckets_[bucket]:
                res.append((bucket, key))
        return res

    def __call__(self, awsAccessKey='', awsSecretKey=''):
        return InMemoryS3Interface(self.state_, self.machine_, awsAccessKey, awsSecretKey)


class InMemoryS3Interface(S3Interface.S3Interface):
    def __init__(self, state, machine, awsAccessKey='', awsSecretKey=''):
        S3Interface.S3Interface.__init__(self)
        self.credentials_ = (awsAccessKey, awsSecretKey)
        self.state_ = state
        self.machine_ = machine

    def initiateMultipartUpload(self, bucketName, eventualKeyName):
        prefix = "__multipart__" + eventualKeyName
        return prefix

    def completeMultipartUpload(self, bucketName, eventualKeyName, uploadId):
        keys = self.listKeysWithPrefix(bucketName, uploadId)

        partIdsAndKeys = sorted([(int(keyname[len(uploadId):]),keyname) for keyname,_,_ in keys])
        res = ""

        assert len(partIdsAndKeys) <= 1000

        for _,keyname in partIdsAndKeys:
            res = res + self.getKeyValue(bucketName, keyname)
            self.deleteKey(bucketName, keyname)

        self.setKeyValue(bucketName, eventualKeyName, res)

    def setMultipartUploadPart(self, bucketName, eventualKeyName, uploadId, oneBasedPartNumber, value):
        """Perform a portion of a multipart upload"""
        assert oneBasedPartNumber >= 1 and oneBasedPartNumber <= 10000
        self.setKeyValue(bucketName, uploadId + str(oneBasedPartNumber), value)

    def listBuckets(self):
        """Return a list of bucket names"""
        with self.state_.lock:
            return self.state_.listBuckets(self.credentials_)

    def listKeysAndSizes(self, bucketName):
        """Return a list of (name, size) pairs of keys in the bucket"""
        with self.state_.lock:
            if bucketName not in self.state_.buckets_:
                raise S3Interface.BucketNotFound(bucketName)

            self.state_.validateAccess(bucketName, self.credentials_)

            return [(key, len(val.value), val.mtime)
                    for key, val in self.state_.buckets_[bucketName].iteritems()]

    def listKeysWithPrefix(self, bucketName, prefix):
        """Return a list of (name, size) pairs of keys in the bucket
        whose names start with a prefix"""
        with self.state_.lock:
            self.state_.validateAccess(bucketName, self.credentials_)
            return [(key, sz, mtime)
                    for key, sz, mtime in self.listKeysAndSizes(bucketName)
                    if key.startswith(prefix)
                   ]

    def getKeyValue(self, bucketName, keyName, logBytes = True):
        """return the value of a key. raises KeyNotFound if it doesn't exist."""
        with self.state_.lock:
            if bucketName not in self.state_.buckets_:
                raise S3Interface.BucketNotFound(bucketName)

            self.state_.validateAccess(bucketName, self.credentials_)

            if keyName not in self.state_.buckets_[bucketName]:
                raise S3Interface.KeyNotFound(bucketName, keyName)

            result = self.state_.buckets_[bucketName][keyName].value

        if logBytes:
            self.state_.logBytesLoadedAndDelay(self.machine_, len(result))

        return result

    def deleteKey(self, bucketName, keyName):
        """Delete a key. Throws exceptions if the key doesn't exist or can't be deleted."""
        with self.state_.lock:
            if bucketName not in self.state_.buckets_:
                self.state_.createBucket(bucketName, self.credentials_)

            self.state_.validateAccess(bucketName, self.credentials_)

            if keyName not in self.state_.buckets_[bucketName]:
                raise S3Interface.KeyNotFound(bucketName, keyName)

            del self.state_.buckets_[bucketName][keyName]

    def getKeyValueOverRange(self, bucketName, keyName, lowIndex, highIndex):
        """return the value of a key. raises KeyNotFound if it doesn't exist."""
        with self.state_.lock:
            self.state_.validateAccess(bucketName, self.credentials_)
            result = self.getKeyValue(bucketName, keyName, logBytes = False)[lowIndex:highIndex]

        self.state_.logBytesLoadedAndDelay(self.machine_, len(result))

        return result

    def getKeySize(self, bucketName, keyName):
        """return the size of a key. raises KeyNotFound if it doesn't exist."""
        with self.state_.lock:
            self.state_.validateAccess(bucketName, self.credentials_)
            return len(self.getKeyValue(bucketName, keyName, logBytes = False))

    def keyExists(self, bucketName, keyName):
        """Returns a bool indicating whether the key exists"""
        with self.state_.lock:
            self.state_.validateAccess(bucketName, self.credentials_)
            if bucketName not in self.state_.buckets_:
                return False
            return keyName in self.state_.buckets_[bucketName]

    def bucketExists(self, bucketName):
        """Returns a bool indicating whether the bucket exists"""
        with self.state_.lock:
            return bucketName in self.state_.buckets_

    def setKeyValue(self, bucketName, keyName, value):
        """sets key 'keyName' in bucket 'bucketName' to value.

        creates the key and the bucket if they don't exist.
        """
        with self.state_.lock:
            if self.state_.writeFailureInjector is not None:
                if self.state_.writeFailureInjector(bucketName, keyName):
                    raise S3Interface.UnableToWriteKey(bucketName, keyName)

            assert isinstance(value, str)

            if bucketName not in self.state_.buckets_:
                self.state_.createBucket(bucketName, self.credentials_)

            self.state_.validateAccess(bucketName, self.credentials_)

            self.state_.buckets_[bucketName][keyName] = InMemoryS3Key(value=value,
                                                                      mtime=time.time())

        if self.state_.delayAfterWriteFunction is not None:
            delay = self.state_.delayAfterWriteFunction(bucketName, keyName)
            time.sleep(delay)

    def setKeyValueFromFile(self, bucketName, keyName, filePath):
        """not implemented in InMemoryS3Interface"""
        pass


