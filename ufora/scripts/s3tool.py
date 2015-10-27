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

import sys

import boto
import boto.s3

command = sys.argv[1]
conn = boto.connect_s3()

if command == "upload":
    bucketname = sys.argv[2]
    keyname = sys.argv[3]
    filename = sys.argv[4]

    bucket = conn.get_bucket(bucketname)
    key = bucket.new_key(keyname)
    key.set_contents_from_filename(filename)
elif command == "download":
    bucketname = sys.argv[2]
    keyname = sys.argv[3]
    filename = sys.argv[4]

    bucket = conn.get_bucket(bucketname)
    key = bucket.new_key(keyname)
    key.get_contents_to_filename(filename)
elif command == "list":
    bucketname = sys.argv[2]

    bucket = conn.get_bucket(bucketname)
    keys = bucket.get_all_keys()

    for key in keys:
        print key
else:
    raise Exception("unknown command: %s" % command)

