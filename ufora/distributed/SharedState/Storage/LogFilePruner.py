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

import argparse
import os
import logging
import traceback
import struct
import binascii


def produceIndexedFileDict(baseDir, prefix):
    return dict([(int(x.split('-')[1], 16), os.path.join(baseDir, x))
            for x in os.listdir(os.path.join(baseDir)) if x.split('-')[0] == prefix])


def stateFileIsValid(path):
    with open(path) as stateFile:
        crc = struct.unpack('i', stateFile.read(struct.calcsize('i')))[0]
        size = struct.unpack('Q', stateFile.read(struct.calcsize('Q')))[0]
        rest = stateFile.read()
        calculatedCrc = binascii.crc32(rest)
        return len(rest) == size and calculatedCrc == crc


def deleteRedundantFiles(afterIndex, logFiles, stateFiles):
    logfilesToDelete = [path for ix, path in logFiles.iteritems() if ix <= afterIndex]
    stateFilesToDelete = [path for ix, path in stateFiles.iteritems() if ix < afterIndex]

    logging.info("Deleting redundant log files: %s", logfilesToDelete)
    for path in sorted(logfilesToDelete):
        os.unlink(path)
    logging.info("Deleting redundant state files: %s", stateFilesToDelete)
    for path in sorted(stateFilesToDelete):
        os.unlink(path)


def pruneLogFiles(baseDir):
    for keyspace in os.listdir(baseDir):
        for dimension in os.listdir(os.path.join(baseDir, keyspace)):
            logFilesBaseDir = os.path.join(baseDir, keyspace, dimension)
            logFiles = produceIndexedFileDict(logFilesBaseDir, 'LOG')
            stateFiles = produceIndexedFileDict(logFilesBaseDir, 'STATE')
            lastGoodStateIndex = None
            for index, path in stateFiles.iteritems():
                try:
                    if stateFileIsValid(path):
                        lastGoodStateIndex = max(lastGoodStateIndex, index)
                except:
                    logging.warn("Invalid state file: %s. Error:\n%s",
                                 path,
                                 traceback.format_exc())
            if lastGoodStateIndex is not None:
                deleteRedundantFiles(lastGoodStateIndex, logFiles, stateFiles)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('ssCacheDir')
    parsed = parser.parse_args()
    pruneLogFiles(parsed.ssCacheDir)

