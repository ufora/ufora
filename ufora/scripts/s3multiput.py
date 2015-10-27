#!/usr/bin/env python

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

import boto
import sys	
import threading
import multiprocessing
import Queue

c = boto.connect_s3()


def uploadThread(mpUpload, fileQueue):
    while True:
        try:
            ix, fileName = fileQueue.get(False)
            with open(fileName, 'rb') as fp:
                mpUpload.upload_part_from_file(fp, ix)
                print 'finished upload of %s' % fileName
        except Queue.Empty:
            return	



if __name__ == "__main__":
    if len(sys.argv) < 4:
        print "usage: s3multiput.py <bucket_name> <key_name> <pattern_glob> "
    else:
        files = sys.argv[3:]
        bucketName = sys.argv[1]
        keyName = sys.argv[2]
        b = c.get_bucket(bucketName)
        mpUpload = b.initiate_multipart_upload(keyName)
        workQueue = Queue.Queue()
        for ix, fileName in enumerate(files):
            workQueue.put((ix + 1, fileName))
        threads = [threading.Thread(target=uploadThread, args=(mpUpload,workQueue)) for x in range(multiprocessing.cpu_count())]
        for t in threads:
            t.start()
        for t in threads:
            t.join()						
        assert workQueue.empty()
        mpUpload.complete_upload()


