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

import errno
import tempfile
import os
import logging
import threading
import random
import shutil
import struct
import unittest
import ufora.native.Storage as Storage


crcType = 'i'
sizeType = 'Q'

class OpenFilesWrapper(object):
    '''
    An object designed implement the ChecksummedWriter interface using a path and
    OpenFiles. This allows us to reuse the test code
    '''
    def __init__(self, path, openFiles):
        self.openFiles = openFiles
        self.path = path

    def path(self):
        return self.path

    def flush(self):
        return self.openFiles.flush(self.path)

    def writeString(self, string):
        return self.openFiles.append(self.path, string)

    def written(self):
        return self.openFiles.written(self.path)

    def fileSize(self):
        return self.written()


def getOwnOpenFds():
    return os.listdir('/proc/%s/fd/' % os.getpid())

class FileIOTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.curFileNumber = 0

    def tearDown(self):
        shutil.rmtree(self.directory, True)

    def nextTempFilePath(self):
        self.curFileNumber += 1
        return os.path.join(self.directory, 'tmp%s' % self.curFileNumber)


    def test_basic(self):
        path = self.nextTempFilePath()
        writer = Storage.ChecksummedWriter(path)
        toWrite = ['asdfasdfasdf', 'asdfasdfasdfasdfasdf', 'asdfsdfikjlkhjgkl']
        for string in toWrite:
            writer.writeString(string)
        writer.flush()
        self.assertEqual(writer.written(), writer.fileSize())
        self.assertEqual(
                writer.written(),
                sum(len(x) + struct.calcsize(crcType) + struct.calcsize(sizeType) for x in toWrite))
        self.assertEqual(writer.path(), path)
        self.assertEqual(os.stat(path).st_size, writer.written())
        success, contents = Storage.readToVector(path)
        self.assertTrue(success)
        self.assertEqual(tuple(toWrite), tuple(contents))
        os.unlink(path)


    def corrupted_read(self, writerFactory, toWrite, lastData, corruptFun, successExpected):
        path = self.nextTempFilePath()
        writer = writerFactory(path)
        ioWrite = ['asdfasdfasdf', 'asdfasdfasdfasdfasdf', 'asdfsdfikjlkhjgkl']
        for string in toWrite:
            writer.writeString(string)
        writer.flush()

        start = writer.fileSize()
        self.assertEqual(os.stat(path).st_size, start)

        writer.writeString(lastData)
        writer.flush()

        with open(path, 'a+') as f:
            f.seek(start)
            bytes = f.read()
            f.truncate(start)

            crc = struct.unpack(crcType, bytes[:struct.calcsize(crcType)])[0]
            size = struct.unpack(crcType, bytes[struct.calcsize(crcType):struct.calcsize(sizeType)])[0]
            message = bytes[struct.calcsize(crcType) + struct.calcsize(sizeType):]

            dat = corruptFun(crc, size, message)
            f.write(dat)

        success, vec = Storage.readToVector(path)
        self.assertEqual(success, successExpected)
        os.unlink(path)

    def corrupted_readers(self, writerFactory):
        # correct
        self.corrupted_read(writerFactory, ['asdfasdf', 'asdfasdfasdf'], 'last piece of data',
                lambda c, s, m : struct.pack(crcType, c) + struct.pack(sizeType, s) +  m, True)

        # size too big
        self.corrupted_read(writerFactory, ['asdfasdf', 'asdfasdfasdf'], 'last piece of data',
                lambda c, s, m : struct.pack(crcType, c) + struct.pack(sizeType, s + 1) +  m, False)

        # size too small
        self.corrupted_read(writerFactory, ['asdfasdf', 'asdfasdfasdf'], 'last piece of data',
                lambda c, s, m : struct.pack(crcType, c) + struct.pack(sizeType, s - 1) +  m, False)

        #crc off
        self.corrupted_read(writerFactory, ['asdfasdf', 'asdfasdfasdf'], 'last piece of data',
                lambda c, s, m : struct.pack(crcType, c + 1) + struct.pack(sizeType, s) +  m, False)

        #message truncated
        for ix in range(20):
            self.corrupted_read(writerFactory, ['asdfasdf', 'asdfasdfasdf'], 'last piece of data',
                    lambda c, s, m : struct.pack(crcType, c) + struct.pack(sizeType, s) +  m[:(ix * -1)], False)

    def test_checksummed_file_corrupted(self):
        self.corrupted_readers(Storage.ChecksummedWriter)

    def test_open_files(self):
        fdsOpenBefore = len(getOwnOpenFds())
        self.openFiles = Storage.OpenFiles(1)
        self.corrupted_readers(lambda path : OpenFilesWrapper(path, self.openFiles))
        self.assertEqual(fdsOpenBefore + 1, len(getOwnOpenFds()))

    def test_open_files_multithreaded(self):
        # test multiple threads in C++ to test OpenFiles for race conditions

        self.openFiles = Storage.OpenFiles(10)
        numThreads = 10
        numValues = 20
        valueSize = 128
        iters = 20
        base = tempfile.mkdtemp()
        numFilesPerThread = 100
        numFiles = 1000


        def genValues(num, size):
            return [''.join(chr(random.randint(ord('A'), ord('z'))) for y in range(size))
                    for x in range(num)]

        files = [os.path.join(base, 'test-path-%s' % ix) for ix in range(numFiles)]

        def writer(files, strings, iters, ix):
            Storage.writeToOpenFiles(
                    self.openFiles,
                    files,
                    strings,
                    iters)

        threads = [threading.Thread(
            target=writer,
            args=(
                random.sample(files, numFilesPerThread),
                genValues(numValues, valueSize),
                iters,
                ix))
            for ix in range(numThreads)]

        for t in threads:
            t.start();

        for t in threads:
            t.join();

        print len(os.listdir(base))
        shutil.rmtree(base)

    @unittest.skip("doesn't work in docker")
    def test_out_of_disk_space_message(self):
        # this test can only be run as root becasue it needs to create
        # a tmpfs temporary partition to invoke the correct exception
        def executeTest(ramdiskdir):
            openFiles = Storage.OpenFiles(10)
            os.system('mount -t tmpfs -o size=1M tmpfs %s' % ramdiskdir)
            try:
                paths = [os.path.join(ramdiskdir, 'test-%s' % ix) for ix in range(10)]
                toWrite = [chr((ix + c) % 255) for c in range(1024) for ix in range(32)] * 32
                for string in toWrite:
                    path = random.choice(paths)
                    openFiles.append(path, string)
            except OSError as e:
                self.assertEqual(e.errno, errno.ENOSPC)
                openFiles.shutdown()
                raise
        if os.geteuid() == 0:
            ramdiskdir = tempfile.mkdtemp()
            self.assertRaises(OSError, lambda : executeTest(ramdiskdir))
            self.assertTrue(os.system('umount %s' %  ramdiskdir) == 0)
        else:
            logging.warn("this test must be run as a superuser!")

