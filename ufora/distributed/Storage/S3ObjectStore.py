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

class S3ObjectStore():
    def __init__(self, s3InterfaceFactory, bucketName, prefix=""):
        self.s3InterfaceFactory = s3InterfaceFactory
        self.bucketName = bucketName
        self.prefix = prefix

    def readValue(self, key):
        try:
            key = self.fullKey(key)
            s3Interface = self.s3InterfaceFactory()
            return s3Interface.getKeyValue(self.bucketName, key)
        except S3Interface.S3InterfaceError as e:
            raise Exception("Error reading from S3 : %s/%s:\n%s" % (self.bucketName, key, e))

    def writeValue(self, key, value):
        try:
            key = self.fullKey(key)
            s3Interface = self.s3InterfaceFactory()
            s3Interface.setKeyValue(self.bucketName, key, value)
        except S3Interface.S3InterfaceError as e:
            raise Exception("Error writing to S3: %s/%s:\n%s" % (self.bucketName, key, e))

    def deleteValue(self, key):
        try:
            key = self.fullKey(key)
            s3Interface = self.s3InterfaceFactory()
            s3Interface.deleteKey(self.bucketName, key)
        except S3Interface.S3InterfaceError as e:
            raise Exception("Error deleting S3 key: %s/%s:\n%s" % (self.bucketName, key, e))

    def listValues(self, prefix=''):
        try:
            prefix = self.fullKey(prefix)
            s3Interface = self.s3InterfaceFactory()
            prefixLen = len(self.prefix)
            return [
                (key[prefixLen:], size, mtime)
                for key, size, mtime in s3Interface.listKeysWithPrefix(self.bucketName, prefix)
                ]
        except S3Interface.S3InterfaceError as e:
            raise Exception("Error listing S3 keys under: %s/%s:\n%s" % (
                self.bucketName, prefix, e
                ))

    def fullKey(self, key):
        return self.prefix + key




