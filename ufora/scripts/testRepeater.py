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

import subprocess
import sys

def main(argv):
    for ix in range(100):
        print argv[1], "starting pass ", ix
        with open("log%s_%s.txt" % (argv[1], ix), "wb") as f:
            try:
                subprocess.check_call(
                    "ulimit -c unlimited; " + " ".join(["python"] + argv[2:]) + " 2> log%s_%s.txt > out%s_%s.txt" % (argv[1], ix, argv[1], ix), 
                    stderr=subprocess.STDOUT,
                    shell=True
                    )
            except subprocess.CalledProcessError as e:
                print "ERRORS in log%s_%s.txt" % (argv[1],ix)
                print >> f, e.output

if __name__ == "__main__":
    main(sys.argv)

