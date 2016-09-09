#   Copyright 2015,2016 Ufora Inc.
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
import os
import ufora
import ufora.config.Mainline as Mainline
import ufora.core.SubprocessRunner as SubprocessRunner
import ufora.config.Setup as Setup
import ufora.FORA.python.Runtime as Runtime

def runSomeFora():
    args = ["/usr/local/bin/python", ufora.rootPythonPath + "/test.py", "-lang", "-langfilter=classTests.fora"]
    returnCode, stdOut, stdErr = SubprocessRunner.callAndReturnResultAndOutput(args)
    assert returnCode == 0

def setUp():
    # clear Compiler Cache and run some test
    ccdir = Setup.config().compilerDiskCacheDir
    filesBefore = os.listdir(ccdir)
    for file in filesBefore:
        filePath = os.path.join(ccdir, file)
        os.remove(filePath)
    runSomeFora()
    
def createParser():
    parser = Setup.defaultParser(
            description='Simulate an Amazon EC2 cluster'
            )

def helperTestDeleteOrCorruptFiles(extension, maxCount, delete=True):
    setUp()
    ccdir = Setup.config().compilerDiskCacheDir
    foundCount = 0
    for file in os.listdir(ccdir):
        if file.endswith(extension):
            foundCount += 1
            filePath = os.path.join(ccdir, file)
            if delete:
                os.remove(filePath)
            else: 
                with open(filePath, "a") as openFile:
                    openFile.write("0")                    
            if foundCount >= maxCount:
                break
    assert foundCount > 0
    runSomeFora()

def testMissingMapFile():
    helperTestDeleteOrCorruptFiles(".map", 1, delete=True)
    
def testMissingDatFiles():
    helperTestDeleteOrCorruptFiles(".dat", 3, delete=True)
    
def testMissingIndexFiles():
    helperTestDeleteOrCorruptFiles(".idx", 3, delete=True)

def testCorruptMapFile():
    helperTestDeleteOrCorruptFiles(".map", 1, delete=False)
    
def testCorruptDatFiles():
    helperTestDeleteOrCorruptFiles(".dat", 3, delete=False)
    
def testCorruptIndexFiles():
    helperTestDeleteOrCorruptFiles(".idx", 3, delete=False)


def main(parsedArguments):
    Runtime.initialize()
 
    testMissingMapFile()
    testMissingDatFiles()
    testMissingIndexFiles()

    testCorruptMapFile()
    testCorruptDatFiles()
    testCorruptIndexFiles()

if __name__ == "__main__":
    Mainline.UserFacingMainline(
        main,
        sys.argv,
        modulesToInitialize=[],
        parser=createParser()
        )

