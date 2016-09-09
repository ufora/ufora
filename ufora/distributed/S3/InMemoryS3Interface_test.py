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
import ufora.distributed.S3.S3Interface as S3Interface
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.config.Setup as Setup

class TestInMemoryS3Interface(unittest.TestCase):
    def test_external_interface(self):
        factory = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        interface = factory("key", "secret_key")
        interface2 = factory("key2", "secret_key_2")

        bucket = "bucket_name"

        self.assertEqual(interface.listBuckets(), [])
        self.assertFalse(interface.bucketExists(bucket))

        interface.setKeyValue(bucket, "a_key", "a_value")

        self.assertEqual(
            [(i[0], i[1]) for i in interface.listKeysAndSizes(bucket)],
            [("a_key", len("a_value"))]
            )

        with self.assertRaises(S3Interface.BucketAccessError):
            interface2.listKeysAndSizes(bucket)


    def test_public_interface(self):
        factory = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        interface = factory("key", "secret_key")
        publicInterface = factory()

        privateBucket = "private_bucket"
        publicBucket = "public_bucket"

        interface.setKeyValue(privateBucket, "private_key", "private_value")
        publicInterface.setKeyValue(publicBucket, "public_key", "public_value")

        #verify the public interface can't see our private bucket
        with self.assertRaises(S3Interface.BucketAccessError):
            publicInterface.listKeysAndSizes(privateBucket)

        #but the public bucket is visible
        self.assertTrue(interface.getKeyValue(publicBucket, "public_key"), "public_value")

        # and we can write to the public bucket too
        interface.setKeyValue(publicBucket, "a_key", "a_value")
        self.assertTrue(publicInterface.getKeyValue(publicBucket, "a_key"), "a_value")

    def test_multipart(self):
        factory = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        publicInterface = factory()

        uploadID = publicInterface.initiateMultipartUpload("aBucket", "aKey")
        publicInterface.setMultipartUploadPart("aBucket", "aKey", uploadID, 1, "this ")
        publicInterface.setMultipartUploadPart("aBucket", "aKey", uploadID, 2, "is ")
        publicInterface.setMultipartUploadPart("aBucket", "aKey", uploadID, 3, "multipart")
        publicInterface.completeMultipartUpload("aBucket", "aKey", uploadID)

        self.assertEqual(publicInterface.getKeyValue("aBucket", "aKey"), "this is multipart")


