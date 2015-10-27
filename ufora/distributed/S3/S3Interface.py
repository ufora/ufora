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

"""an abstraction around Amazon S3"""

#class S3InterfaceCredentials(object):
    #external = False
    #internal = False
    #public = False

    #def __cmp__(self, other):
        #if not isinstance(other, S3InterfaceCredentials):
            #return -1

        #return cmp(self.asTuple(), other.asTuple())

    #def asTuple(self):
        #assert False, "Must be implemented by derived class"

#class ExternalS3InterfaceCredentials(S3InterfaceCredentials):
    #external=True
    #def __init__(self, accessKey, secretKey):
        #S3InterfaceCredentials.__init__(self)

        #self.accessKey = accessKey
        #self.secretKey = secretKey

    #def asTuple(self):
        #return (ExternalS3InterfaceCredentials, self.accessKey, self.secretKey)

#class PublicS3InterfaceCredentials(S3InterfaceCredentials):
    #public = True

    #def __init__(self):
        #S3InterfaceCredentials.__init__(self)

    #def asTuple(self):
        #return (PublicS3InterfaceCredentials,)

#class InternalS3InterfaceCredentials(S3InterfaceCredentials):
    #internal=True
    #def __init__(self):
        #S3InterfaceCredentials.__init__(self)

    #def asTuple(self):
        #return (InternalS3InterfaceCredentials,)



class S3InterfaceError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class BucketNotFound(S3InterfaceError):
    def __init__(self, bucketName):
        S3InterfaceError.__init__(self, "Bucket not found: %s" % bucketName)

class BucketAccessError(S3InterfaceError):
    def __init__(self, bucketName):
        S3InterfaceError.__init__(
            self,
            "Bucket not accessible under these credentials: %s" % bucketName
            )

class KeyAccessError(S3InterfaceError):
    def __init__(self, bucketNameOrMessage, keyName=None):
        if keyName is None:
            S3InterfaceError.__init__(self, bucketNameOrMessage)
        else:
            S3InterfaceError.__init__(
                self,
                "Bucket/key not accessible under these credentials: %s/%s" % (
                    bucketNameOrMessage, keyName)
                )

class KeyNotFound(S3InterfaceError):
    def __init__(self, bucketNameOrMessage, keyName=None):
        if keyName is None:
            S3InterfaceError.__init__(self, bucketNameOrMessage)
        else:
            S3InterfaceError.__init__(
                self,
                "Key not found: <%s,%s>" % (bucketNameOrMessage, keyName)
                )

class UnableToWriteKey(S3InterfaceError):
    def __init__(self, bucketNameOrMessage, keyName=None):
        if keyName is None:
            S3InterfaceError.__init__(self, bucketNameOrMessage)
        else:
            S3InterfaceError.__init__(
                self,
                "Couldn't write key <%s,%s>" % (bucketNameOrMessage, keyName)
                )

class UnableToDeleteKey(S3InterfaceError):
    def __init__(self, bucketNameOrMessage, keyName=None):
        if keyName is None:
            S3InterfaceError.__init__(self, bucketNameOrMessage)
        else:
            S3InterfaceError.__init__(
                self,
                "Couldn't delete key <%s,%s>" % (bucketNameOrMessage, keyName)
                )

class S3InterfaceFactory(object):
    isCompatibleWithOutOfProcessDownloadPool = True

    def __call__(self, awsAccessKey='', awsSecretKey=''):
        """ Returns an S3Interface """
        raise NotImplementedError()

    def close(self):
        pass

    #def getInterfaceForExternalBucketsWithCredentials(self, awsAccessKey, awsSecretKey):
        #"""Return an interface that reads under the given credentials.

        #The credentials must be valid and non-empty.  This interface will not be able to see
        #any buckets that are listed under the BSA bucket list.
        #"""
        #pass

    #def getInterfaceForPublicBuckets(self):
        #"""Return an interface that will read from public buckets under the login credentials.

        #This interface will not be able to see anything in the internal account.
        #"""
        #pass

    #def getInterfaceForInternalBuckets(self):
        #"""Return an interface that will read from our private buckets only.

        #This interface will only be able to access 'bucketname' which must be one of our internal
        #buckets."""
        #pass

class S3Interface(object):
    publicCredentials = ('', '')

    """Base class for S3Interfaces"""
    def initiateMultipartUpload(self, bucketName, eventualKeyName):
        """Initiate a multipart upload and return the uploadId"""
        assert False, "Subclasses implement"

    def completeMultipartUpload(self, bucketName, eventualKeyName, uploadId):
        """Complete a multipart upload"""
        assert False, "Subclasses implement"

    def setMultipartUploadPart(self,
                               bucketName,
                               eventualKeyName,
                               uploadId,
                               oneBasedPartNumber,
                               value):
        """Perform a portion of a multipart upload"""
        assert False, "Subclasses implement"

    def listBuckets(self):
        """Return a list of bucket names"""
        assert False, "Subclasses implement"

    def listKeysAndSizes(self, bucketName):
        """Return a list of (name, size) pairs of keys in the bucket"""
        assert False, "Subclasses implement"

    def listKeysWithPrefix(self, bucketName, prefix):
        """Return a list of (name, size) pairs of keys in the bucket
        whose names start with a prefix"""
        assert False, "Subclasses implement"

    def getKeyValue(self, bucketName, keyName):
        """return the value of a key. raises KeyNotFound if it doesn't exist."""
        assert False, "Subclasses implement"

    def getKeyValueOverRange(self, bucketName, keyName, lowIndex, highIndex):
        """return the value of a key. raises KeyNotFound if it doesn't exist."""
        assert False, "Subclasses implement"

    def getKeySize(self, bucketName, keyName):
        """return the size of a key. raises KeyNotFound if it doesn't exist."""
        assert False, "Subclasses implement"

    def keyExists(self, bucketName, keyName):
        """Returns a bool indicating whether the key exists"""
        assert False, "Subclasses implement"

    def bucketExists(self, bucketName):
        """Returns a bool indicating whether the bucket exists"""
        assert False, "Subclasses implement"

    def setKeyValue(self, bucketName, keyName, value):
        """sets key 'keyName' in bucket 'bucketName' to value.

        creates the key and the bucket if they don't exist.
        """
        assert False, "Subclasses implement"

    def setKeyValueFromFile(self, bucketName, keyName, filePath):
        """sets the value of key 'keyName' in bucket 'bucketName' to the content of a file."""
        assert False, "Subclasses implement"

