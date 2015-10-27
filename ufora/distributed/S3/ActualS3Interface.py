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
import datetime
import boto
import boto.utils
import logging
import os
import traceback
import StringIO

BUFFER_SIZE_OVERRIDE = 256 * 1024 * 1024

class BotoKeyFileObject(object):
    def __init__(self, key):
        self.key = key
        self.bytesRead = 0
        self.totalBytes = key.size

    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

    def read(self, bytes):
        if bytes <= 0:
            return ""

        data = self.key.read(bytes)
        self.bytesRead += len(data)

        while bytes > 0 and data == "" and self.bytesRead < self.totalBytes:
            data = self.key.read(bytes)
            self.bytesRead += len(data)

        return data

    def next(self):
        if self.bytesRead == self.totalBytes:
            raise StopIteration()
        return self.read(BUFFER_SIZE_OVERRIDE)

    def tell(self):
        return self.bytesRead

    def seek(self):
        assert False, "Not implemented"

    def write(self, *args):
        assert False, "BotoKeyFileObjects are not writeable"


class ActualS3InterfaceFactory(S3Interface.S3InterfaceFactory):
    def __call__(self, awsAccessKey='', awsSecretKey=''):
        return ActualS3Interface((awsAccessKey, awsSecretKey))

    def withMachine(self, machine):
        return self

def parseS3Timestamp(timestamp):
    diff_from_epoch = boto.utils.parse_ts(timestamp) - datetime.datetime.utcfromtimestamp(0)
    return diff_from_epoch.total_seconds()

class ActualS3Interface(S3Interface.S3Interface):
    """implements a model for Amazon's S3 service using boto"""
    def __init__(self, credentials):
        self.credentials_ = credentials

    def connectS3(self):
        if not boto.config.has_section('Boto'):
            boto.config.add_section('Boto')

        # override the default super-long timeout in boto.
        # boto automatically retries timed out requests so it's best to keep a
        # short timeout because S3 can sometimes (about 1 in 10 requests) stall
        # for a long time.
        boto.config.set('Boto', 'http_socket_timeout', '5')
        boto.config.set('Boto', 'metadata_service_num_attempts', '10')

        az = os.getenv('AWS_AVAILABILITY_ZONE')
        logging.info('AZ variable is: %s', az)

        credentials = self.credentials_
        if credentials == S3Interface.S3Interface.publicCredentials:
            credentials = (None, None)

        boto_args = {
            'aws_access_key_id': credentials[0],
            'aws_secret_access_key': credentials[1]
            }
        if az:
            return boto.s3.connect_to_region(az[:-1], **boto_args)
        else:
            return boto.connect_s3(**boto_args)

    def initiateMultipartUpload(self, bucketName, eventualKeyName):
        b = self.openOrCreateBucket_(bucketName)
        return str(b.initiate_multipart_upload(eventualKeyName).id)

    def completeMultipartUpload(self, bucketName, eventualKeyName, uploadId):
        """Complete a multipart upload"""
        b = self.openOrCreateBucket_(bucketName)
        mp = boto.s3.multipart.MultiPartUpload(b)
        mp.key_name = eventualKeyName
        mp.id = uploadId

        mp.complete_upload()

    def setMultipartUploadPart(self, bucketName, eventualKeyName, uploadId, oneBasedPartNumber, value):
        """Perform a portion of a multipart upload"""
        stringAsFile = StringIO.StringIO(value)

        b = self.openOrCreateBucket_(bucketName)
        mp = boto.s3.multipart.MultiPartUpload(b)
        mp.key_name = eventualKeyName
        mp.id = uploadId

        mp.upload_part_from_file(stringAsFile, oneBasedPartNumber)

    def close(self):
        pass

    def listBuckets(self):
        """return a list of bucket names available in s3"""
        s3 = self.connectS3()
        return [str(bucket.name) for bucket in s3.get_all_buckets()]

    def listKeysAndSizes(self, bucketName):
        """return a list of (keyname,keysize) tuples in a bucket"""
        return self.listKeysWithPrefix(bucketName, None)

    def listKeysWithPrefix(self, bucketName, prefix):
        """return a list of (keyname,keysize) tuples in a bucket"""
        options = {} if prefix is None else {"prefix": prefix}
        bucket = self.openBucket_(bucketName)
        return [(str(key.name), key.size, parseS3Timestamp(key.last_modified))
                for key in bucket.get_all_keys(**options)]

    def getKeyValue(self, bucketName, keyName):
        """return the value of a key. raises KeyNotFound if it doesn't exist."""
        key = self.openKey_(bucketName, keyName)
        return key.get_contents_as_string()

    def getKeyValueOverRange(self, bucketName, keyName, lowIndex, highIndex):
        key = self.openKey_(bucketName, keyName)
        return key.get_contents_as_string(
            headers={"Range": "bytes=%s-%s" % (lowIndex, highIndex - 1)}
            )

    def getKeySize(self, bucketName, keyName):
        return self.openKey_(bucketName, keyName).size

    def openKey_(self, bucketName, keyName, overrides=None):
        """return a boto key object. raises KeyNotFound if it doesn't exist."""
        # we don't verify access to the bucket because it's possible that
        # we have acess to read the key but not the bucket
        bucket = self.openBucket_(bucketName, verifyAccess=False)
        key = bucket.get_key(keyName)
        if key is None:
            raise S3Interface.KeyNotFound(bucketName, keyName)
        key.BufferSize = BUFFER_SIZE_OVERRIDE
        return key

    def tryOpenBucket_(self, bucketName, verifyAccess=True):
        s3 = self.connectS3()
        try:
            bucket = s3.get_bucket(bucketName, validate=verifyAccess)
            return bucket
        except:
            return None

    def openBucket_(self, bucketName, verifyAccess=True):
        bucket = self.tryOpenBucket_(bucketName, verifyAccess)
        if bucket is None:
            raise S3Interface.BucketNotFound(bucketName)
        return bucket

    def keyExists(self, bucketName, keyName):
        """Returns a bool indicating whether the key exists"""
        # we don't verify access to the bucket because it's possible that
        # we have acess to read the key but not the bucket
        bucket = self.tryOpenBucket_(bucketName, verifyAccess=False)
        if bucket is None:
            return False

        key = bucket.get_key(keyName)
        return key is not None

    def deleteKey(self, bucketName, keyName):
        # we don't verify access to the bucket because it's possible that
        # we have acess to read the key but not the bucket
        bucket = self.tryOpenBucket_(bucketName, verifyAccess=False)
        if bucket is None:
            return False

        key = bucket.get_key(keyName)
        if key is None:
            raise S3Interface.KeyNotFound(bucketName, keyName)

        key.delete()

    def bucketExists(self, bucketName):
        """Returns a bool indicating whether the bucket exists"""
        bucket = self.tryOpenBucket_(bucketName)
        return bucket is not None

    def setKeyValue(self, bucketName, keyName, value):
        """sets key 'keyName' in bucket 'bucketName' to value.

        creates the key and the bucket if they don't exist.
        """
        bucket = self.openOrCreateBucket_(bucketName)
        k = self.openOrCreateKey_(bucket, keyName)
        k.set_contents_from_string(value)

    def setKeyValueFromFile(self, bucketName, keyName, filePath):
        bucket = self.openOrCreateBucket_(bucketName)
        k = self.openOrCreateKey_(bucket, keyName)
        k.set_contents_from_filename(filePath)

    def openOrCreateBucket_(self, bucketName):
        s3 = self.connectS3()
        bucket = None
        attempts = 0

        while bucket is None:
            bucket = s3.get_bucket(bucketName)
            if bucket is None:
                try:
                    bucket = s3.create_bucket(bucketName)
                except:
                    attempts += 1
                    if attempts > 3:
                        logging.error("Failed to create a bucket. Giving up.:\n%s",
                                      traceback.format_exc())
                        raise

                    logging.warn("error creating a bucket - trying again:\n %s",
                                 traceback.format_exc())
        return bucket

    def openOrCreateKey_(self, bucket, keyName):
        k = bucket.get_key(keyName)
        if k is None:
            k = bucket.new_key(keyName)
        if k is None:
            logging.warn("couldn't get amazon S3 bucket '%s'", bucket.name)
            raise S3Interface.UnableToWriteKey(bucket.name, keyName)
        return k


