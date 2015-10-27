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

import os
import sys
import time
import ufora.config.Mainline as Mainline
import ufora.util.SubprocessingModified as subprocess

# importing the interpreter as a module to find its path here.
# so if we ever decide to move the interpreter it, this file
# should appear as a dependent module

def removeFirstLine(string):
    return string[string.find('\n') + 1:]

def testInMem():
    val = subprocess.Popen(
        ['fora -e "1+2"'],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        #make sure we pass the script-setup environment variables down
        env = dict(os.environ)
        ).communicate()

    if removeFirstLine(val[0]).lstrip().rstrip() == '3':
        return True
    print 'testInMem failed:', val
    return False

def main(parsedArguments):
    if testInMem():
        return 0
    return 1

if __name__ == "__main__":
    Mainline.UserFacingMainline(main, sys.argv)

