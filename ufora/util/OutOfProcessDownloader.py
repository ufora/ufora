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

import logging
import traceback
import time
import threading
import ufora.util.ManagedThread as ManagedThread
import sys
import struct
import os
import ufora.distributed.util.common as common
import cPickle as pickle
import Queue as Queue
import ufora.core.SubprocessRunner as SubprocessRunner

BYTE_DATA = "D"
BYTE_EXCEPTION = "E"
FORK_START_TIMEOUT = 5.0

class HeartbeatLogger:
    def __init__(self, msg, timeout = 1.0):
        self.msg = msg
        self.t0 = None
        self.timeout = timeout
        self.thread = threading.Thread(target=self)
        self.completedQueue = Queue.Queue()

    def start(self):
        self.t0 = time.time()
        self.thread.start()

    def __call__(self):
        while True:
            try:
                self.completedQueue.get(True, self.timeout)
                logging.info("Heartbeat %s completed after %s", self.msg, time.time() - self.t0)
                return
            except Queue.Empty:
                logging.info(
                    "Heartbeat %s still active after %s seconds",
                    self.msg,
                    time.time() - self.t0
                    )

    def stop(self):
        self.completedQueue.put(None)
        self.thread.join()

class OutOfProcessDownloader:
    """A worker that can answer queries in another process and return their results as strings.

    Queries must be pickleable callables. Clients will either receive an exception or have
    the result passed to them as a file descriptor and a bytecount containing the answer.
    """

    def __init__(self, actuallyRunOutOfProcess, childPipes = None):
        self.hasStarted = False
        self.isChild = False
        self.childSubprocess = None
        self.backgroundThread = None
        self.lock = threading.Lock()
        self.writeQueue = Queue.Queue()
        self.actuallyRunOutOfProcess = actuallyRunOutOfProcess

        if childPipes is None:
            self.createNewPipes_()
        else:
            self.childWriteFD, self.childReadFD = childPipes
            self.isChild = True

            self.closeAllUnusedFileDescriptors()

    def closeAllUnusedFileDescriptors(self):
        #we need to ensure that we don't hold sockets open that we're not supposed to
        maxFD = os.sysconf("SC_OPEN_MAX")

        for fd in range(3, maxFD):
            if fd not in (self.childWriteFD, self.childReadFD):
                try:
                    os.close(fd)
                except:
                    pass

    def createNewPipes_(self):
        self.parentReadFD, self.childWriteFD = os.pipe()
        self.childReadFD, self.parentWriteFD = os.pipe()

    def closeAllPipes_(self):
        os.close(self.parentReadFD)
        os.close(self.parentWriteFD)
        os.close(self.childReadFD)
        os.close(self.childWriteFD)


    def start(self):
        assert not self.hasStarted

        if self.actuallyRunOutOfProcess:
            def onStdout(msg):
                logging.info("OutOfProcessDownloader Out> %s", msg)

            def onStderr(msg):
                logging.info("OutOfProcessDownloader Err> %s", msg)

            self.childSubprocess = SubprocessRunner.SubprocessRunner(
                [sys.executable, __file__, str(self.childWriteFD), str(self.childReadFD)],
                onStdout,
                onStderr
                )
            self.childSubprocess.start()
            self.hasStarted = True
        else:
            self.hasStarted = True
            self.backgroundThread = ManagedThread.ManagedThread(target=self.executeChild_)
            self.backgroundThread.start()

    def stop(self):
        with self.lock:
            if self.actuallyRunOutOfProcess:
                self.childSubprocess.stop()
                self.childSubprocess = None
                self.closeAllPipes_()
            else:
                self.writeQueue.put(None)
                self.backgroundThread.join()

                self.closeAllPipes_()

            self.hasStarted = False

    def executeChild_(self):
        logging.info("Child started with %s, %s", self.childWriteFD, self.childReadFD)
        self.hasStarted = True
        self.isChild = True

        try:
            while True:
                if self.actuallyRunOutOfProcess:
                    isException, outgoingMessage = self.runOutOfProc()
                else:
                    isException, outgoingMessage = self.runInProc()
                    if not isException and outgoingMessage is None:
                        return

                finalValueToWrite = (
                    (BYTE_EXCEPTION if isException else BYTE_DATA) +
                    common.longToString(len(outgoingMessage)) + outgoingMessage
                    )

                os.write(self.childWriteFD, finalValueToWrite)
        except:
            logging.error("Main OutOfProcessDownloader loop failed: %s", traceback.format_exc())
        finally:
            #bail
            if self.actuallyRunOutOfProcess:
                os._exit(0)

    def runOutOfProc(self):
        isException = None
        outgoingMessage = None

        callableSize = common.stringToLong(os.read(self.childReadFD, 4))
        msgCallable = os.read(self.childReadFD, callableSize)
        inputSize = common.stringToLong(os.read(self.childReadFD, 4))
        msgInput = os.read(self.childReadFD, inputSize) if inputSize > 0 else None

        t0 = time.time()
        callableObj = None
        heartbeatLogger = None
        try:
            callableObj = pickle.loads(msgCallable)

            heartbeatLogger = HeartbeatLogger(str(callableObj))
            heartbeatLogger.start()

            outgoingMessage = callableObj() if msgInput is None else \
                callableObj(msgInput)

            assert isinstance(outgoingMessage, str), "Callable %s returned %s, not str" % (callableObj, type(outgoingMessage))

            isException = False
        except Exception as e:
            try:
                logging.error(
                    "OutOfProcessDownloader caught exception after %s seconds: %s\n" +
                    "Task was %s",
                    time.time() - t0,
                    traceback.format_exc(),
                    callableObj
                    )
            except:
                logging.error(
                    "OutOfProcessDownloader failed formatting error: %s",
                    traceback.format_exc()
                    )

            isException = True
            outgoingMessage = pickle.dumps(e)
        finally:
            if heartbeatLogger:
                heartbeatLogger.stop()

        return isException, outgoingMessage


    def runInProc(self):
        isException = None
        outgoingMessage = None

        t0 = time.time()
        callback = None

        callback = self.writeQueue.get()
        if callback is None:
            #graceful shutdown message
            return False, None

        try:
            outgoingMessage = callback()

            assert isinstance(outgoingMessage, str), "Callable %s returned %s, not str" % (callback, type(outgoingMessage))

            isException = False
        except Exception as e:
            try:
                logging.error(
                    "OutOfProcessDownloader caught exception after %s seconds: %s\n" +
                    "Task was %s",
                    time.time() - t0,
                    traceback.format_exc(),
                    callback
                    )
            except:
                logging.error(
                    "OutOfProcessDownloader failed formatting error: %s",
                    traceback.format_exc()
                    )

            isException = True
            outgoingMessage = pickle.dumps(e)

        return isException, outgoingMessage

    def executeAndCallback(self, toExecute, outputCallback, inputCallback=None):
        ''' Runs a callable in a separate process, marshalling input/output via callback.

        toExecute      - a callable that can be pickled
        outputCallback - a callback taking a file-descriptor and an integer representing
                         the number of bytes that can be read from the descriptor.
        inputCallback  - a callback that takes a file-descriptor and writes a 4-byte
                         integer representing the size of input followed by the input
                         data itself.
        '''
        with self.lock:
            assert self.hasStarted

            if self.actuallyRunOutOfProcess:
                toSend = pickle.dumps(toExecute)

                os.write(self.parentWriteFD, common.longToString(len(toSend)))
                os.write(self.parentWriteFD, toSend)
                if inputCallback is None:
                    os.write(self.parentWriteFD, common.longToString(0))
                else:
                    inputCallback(self.parentWriteFD)

            else:
                if inputCallback is None:
                    self.writeQueue.put(toExecute)
                else:
                    # fire the callback on a separate thread so we can read from
                    # the pipe while its running and prevernt os.write from
                    # hanging.
                    thread = threading.Thread(target=inputCallback, args=(self.parentWriteFD,))
                    thread.start()

                    inputSize = common.stringToLong(os.read(self.childReadFD, 4))
                    inputData = os.read(self.childReadFD, inputSize)

                    thread.join()
                    self.writeQueue.put(lambda: toExecute(inputData))

            prefix = os.read(self.parentReadFD, 5)

            assert prefix[0] in (BYTE_EXCEPTION, BYTE_DATA), prefix
            isException = prefix[0] == BYTE_EXCEPTION

            msgSize = common.stringToLong(prefix[1:5])

            if isException:
                pickledException = os.read(self.parentReadFD, msgSize)
                raise pickle.loads(pickledException)
            else:
                outputCallback(self.parentReadFD, msgSize)


class OutOfProcessDownloaderPool:
    """Models a pool of out-of-process-downloaders"""
    def __init__(self, maxProcesses, actuallyRunOutOfProcess = True):
        self.downloadersQueue = Queue.Queue()

        self.allDownloaders = []

        for ix in range(maxProcesses):
            downloader = OutOfProcessDownloader(actuallyRunOutOfProcess)
            downloader.start()
            self.downloadersQueue.put(downloader)

            self.allDownloaders.append(downloader)

    def getDownloader(self):
        return OutOfProcessDownloadProxy(self)

    def checkoutDownloader_(self):
        return self.downloadersQueue.get()

    def checkinDownloader_(self, downloader):
        self.downloadersQueue.put(downloader)

    def teardown(self):
        for d in self.allDownloaders:
            d.stop()

class OutOfProcessDownloadProxy:
    """Class that checks out a downloader and executes the result"""
    def __init__(self, pool):
        self.pool = pool

    def executeAndCallbackWithFileDescriptor(self,
                                             toExecute,
                                             callbackTakingFDAndSize,
                                             inputCallback=None):
        """Execute 'toExecute' in another process and pass a filedescriptor and size to the callback.

        If the remote process encounters an exception, we raise that immediately.
        """
        d = self.pool.checkoutDownloader_()

        try:
            d.executeAndCallback(toExecute, callbackTakingFDAndSize, inputCallback)
        finally:
            self.pool.checkinDownloader_(d)

    def executeAndCallbackWithString(self, toExecute, callbackTakingString, inputCallback=None):
        """Execute 'toExecute' in another process and pass the resulting string to the callback.

        If the remote process encounters an exception, we raise that immediately.
        """
        def callbackTakingFDAndSize(fileDescriptor, sz):
            callbackTakingString(os.read(fileDescriptor, sz))

        self.executeAndCallbackWithFileDescriptor(toExecute,
                                                  callbackTakingFDAndSize,
                                                  inputCallback)


def main(argv):
    runner = OutOfProcessDownloader(True, (int(argv[1]), int(argv[2])))
    runner.executeChild_()

if __name__ == '__main__':
    import ufora.config.Setup as Setup

    setup = Setup.defaultSetup()

    setup.config.configureLogging(logging.INFO)

    with Setup.PushSetup(setup):
        main(sys.argv)



