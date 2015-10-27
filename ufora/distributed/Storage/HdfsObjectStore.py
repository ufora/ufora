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

import hdfs.client
from hdfs.util import HdfsError
import logging

import ufora.distributed.Storage.ObjectStore as ObjectStore

class HdfsObjectStore(ObjectStore.ObjectStore):
    def __init__(self, namenode_url, root_dir):
        self.root_dir = root_dir
        self.namenode_url = namenode_url

    @property
    def hdfs_client(self):
        return hdfs.client.Client(self.namenode_url, root=self.root_dir)

    def readValue(self, key):
        logging.info("Reading key '%s'", key)
        data_generator = self.hdfs_client.read(key)
        return ''.join(list(data_generator))

    def writeValue(self, key, value):
        logging.info("Writing key '%s'", key)
        self.hdfs_client.write(key, value)

    def deleteValue(self, key):
        logging.info("Deleting key '%s'", key)
        self.hdfs_client.delete(key)

    def listValues(self, prefix=''):
        values = []
        directories = [prefix]
        hdfs_client = self.hdfs_client
        while len(directories) > 0:
            directory = directories.pop()
            for path, item in hdfs_client.list(directory):
                if item['type'] == "FILE":
                    values.append(
                        (path[len(self.root_dir):], item['length'], item['modificationTime']/1000)
                        )
                elif item['type'] == "DIRECTORY":
                    directories.append(path)
        return values

    def keyExists(self, key):
        try:
            self.hdfs_client.status(key)
            return True
        except HdfsError:
            return False

