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
import json
import argparse
import boto

def main(args):
    parser = argparse.ArgumentParser()

    parser.add_argument('topicArn')
    parser.add_argument('subject')
    parser.add_argument('content')

    parsed = parser.parse_args()

    content = parsed.content
    if parsed.content == '-':
        content = sys.stdin.read()


    c = boto.connect_sns()
    try:
        c.publish(parsed.topicArn, parsed.subject, content)
        return 0

    except Exception as e:
        print json.dumps(json.loads(e.message), indent=2)
        return 1












if __name__ == "__main__":
    sys.exit(main(sys.argv))

