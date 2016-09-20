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
import os
import socket
import ufora.distributed.util.common as common
import cPickle as pickle
import Queue as Queue
import ufora.core.SubprocessRunner as SubprocessRunner

BYTE_DATA = "D"
BYTE_EXCEPTION = "E"

class HeartbeatLogger:
    def __init__(self, msg, timeout=1.0):
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
                logging.debug("Heartbeat %s completed after %s", self.msg, time.time() - self.t0)
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

def readAtLeast(fd, bytecount):
    """Read 'bytecount' bytes from file descriptor fd. raise if we can't."""
    inputData = os.read(fd, bytecount)
    while len(inputData) < bytecount:
        newData = os.read(fd, bytecount - len(inputData))
        assert len(newData) != 0
        inputData += newData
    return inputData

def writeAllToFd(fd, toWrite):
    while toWrite:
        written = os.write(fd, toWrite)
        if written == len(toWrite):
            return

        toWrite = toWrite[written:]
    


    

class OutOfProcessDownloader:
    """A worker that can answer queries in another process and return their results as strings.

    Queries must be pickleable callables. Clients will either receive an exception or have
    the result passed to them as a file descriptor and a bytecount containing the answer.
    """

    def __init__(self, actuallyRunOutOfProcess, childSocket = None):
        self.hasStarted = False
        self.isChild = False
        self.childSubprocess = None
        self.backgroundThread = None
        self.lock = threading.Lock()
        self.writeQueue = Queue.Queue()
        self.actuallyRunOutOfProcess = actuallyRunOutOfProcess

        if childSocket is None:
            self.createNewSocket_()
        else:
            self.childSocket = childSocket
            self.childSocket.setblocking(True)
            self.isChild = True

            self.closeAllUnusedFileDescriptors()

    def __repr__(self):
        return "OOPD(fd=%s/%s)" % (self.childSocket.fileno(), self.parentSocket.fileno())

    def closeAllUnusedFileDescriptors(self):
        #we need to ensure that we don't hold sockets open that we're not supposed to
        maxFD = os.sysconf("SC_OPEN_MAX")

        for fd in range(3, maxFD):
            if fd != self.childSocket.fileno():
                try:
                    os.close(fd)
                except:
                    pass

    def createNewSocket_(self):
        self.parentSocket, self.childSocket = socket.socketpair()

    def closeAllSockets_(self):
        self.parentSocket.close()
        self.childSocket.close()

    def shutdownSockets_(self):
        self.parentSocket.shutdown(socket.SHUT_RDWR)
        self.childSocket.shutdown(socket.SHUT_RDWR)


    def start(self):
        assert not self.hasStarted

        if self.actuallyRunOutOfProcess:
            def onStdout(msg):
                logging.info("OutOfProcessDownloader Out> %s", msg)

            def onStderr(msg):
                logging.info("OutOfProcessDownloader Err> %s", msg)

            self.childSubprocess = SubprocessRunner.SubprocessRunner(
                [sys.executable, __file__, str(self.childSocket.fileno())],
                onStdout,
                onStderr
                )
            self.childSubprocess.start()
            self.hasStarted = True

            self.backgroundThread = ManagedThread.ManagedThread(target=self.watchChild_)
            self.backgroundThread.start()
        else:
            self.hasStarted = True
            self.backgroundThread = ManagedThread.ManagedThread(target=self.executeChild_)
            self.backgroundThread.start()

    def watchChild_(self):
        self.childSubprocess.wait()
        self.hasStarted = False
        self.shutdownSockets_()

    def stop(self):
        with self.lock:
            if self.actuallyRunOutOfProcess:
                self.childSubprocess.stop()
                self.backgroundThread.join()
                self.childSubprocess = None
                self.backgroundThread = None
            else:
                self.writeQueue.put(None)
                self.backgroundThread.join()

                self.hasStarted = False
            self.closeAllSockets_()

    def executeChild_(self):
        logging.debug("Child started with %s, %s", self.childSocket)
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

                writeAllToFd(self.childSocket.fileno(), finalValueToWrite)
        except:
            logging.error("Main OutOfProcessDownloader loop failed: %s", traceback.format_exc())
        finally:
            #bail
            if self.actuallyRunOutOfProcess:
                os._exit(0)

    def runOutOfProc(self):
        isException = None
        outgoingMessage = None

        callableSize = common.stringToLong(readAtLeast(self.childSocket.fileno(), 4))
        msgCallable = readAtLeast(self.childSocket.fileno(), callableSize)

        try:
            callableObj = pickle.loads(msgCallable)
        except Exception as e:
            logging.error(
                "OutOfProcessDownloader failed deserializing the given callable (of size %s): %s",
                callableSize,
                traceback.format_exc()
                )

            isException = True
            outgoingMessage = pickle.dumps(e)
            return isException, outgoingMessage


        direct = False
        try:
            if callableObj.wantsDirectAccessToInputFileDescriptor:
                direct = True
        except AttributeError:
            pass

        if not direct:
            inputSize = common.stringToLong(readAtLeast(self.childSocket.fileno(), 4))
            msgInput = readAtLeast(self.childSocket.fileno(), inputSize) if inputSize > 0 else None
        else:
            msgInput = self.childSocket.fileno()

        t0 = time.time()
        heartbeatLogger = None
        try:
            heartbeatLogger = HeartbeatLogger(str(callableObj))
            heartbeatLogger.start()

            outgoingMessage = callableObj() if msgInput is None else callableObj(msgInput)

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

                writeAllToFd(self.parentSocket.fileno(), common.longToString(len(toSend)))
                writeAllToFd(self.parentSocket.fileno(), toSend)

                if inputCallback is None:
                    writeAllToFd(self.parentSocket.fileno(), common.longToString(0))
                else:
                    inputCallback(self.parentSocket.fileno())

            else:
                if inputCallback is None:
                    self.writeQueue.put(toExecute)
                else:
                    # fire the callback on a separate thread so we can read from
                    # the pipe while its running and prevent os.write from
                    # hanging.
                    def callInputCallback():
                        inputCallback(self.parentSocket.fileno())

                    thread = threading.Thread(target=callInputCallback, args=())
                    thread.start()

                    direct = False
                    try:
                        if toExecute.wantsDirectAccessToInputFileDescriptor:
                            direct = True
                    except AttributeError:
                        pass

                    if direct:
                        def executeFunc():
                            res = toExecute(self.childSocket.fileno())
                            thread.join()
                            return res

                        self.writeQueue.put(executeFunc)
                    else:
                        inputSize = common.stringToLong(readAtLeast(self.childSocket.fileno(), 4))
                        inputData = readAtLeast(self.childSocket.fileno(), inputSize)

                        thread.join()

                        self.writeQueue.put(lambda: toExecute(inputData))

            prefix = readAtLeast(self.parentSocket.fileno(), 5)
            
            if len(prefix) != 5:
                #this downloader is dead
                raise IOError("OutOfProcessDownloader died")

            assert prefix[0] in (BYTE_EXCEPTION, BYTE_DATA), prefix
            isException = prefix[0] == BYTE_EXCEPTION

            msgSize = common.stringToLong(prefix[1:5])

            if isException:
                pickledException = readAtLeast(self.parentSocket.fileno(), msgSize)
                raise pickle.loads(pickledException)
            else:
                outputCallback(self.parentSocket.fileno(), msgSize)


class OutOfProcessDownloaderPool:
    """Models a pool of out-of-process-downloaders"""
    def __init__(self, maxProcesses, actuallyRunOutOfProcess = True):
        self.actuallyRunOutOfProcess = actuallyRunOutOfProcess

        self.downloadersQueue = Queue.Queue()

        self.allDownloaders = []

        for ix in range(maxProcesses):
            self.createDownloader_()

    def createDownloader_(self):
        downloader = OutOfProcessDownloader(self.actuallyRunOutOfProcess)
        downloader.start()
        self.downloadersQueue.put(downloader)
        self.allDownloaders.append(downloader)

    def getDownloader(self):
        return OutOfProcessDownloadProxy(self)

    def checkoutDownloader_(self):
        return self.downloadersQueue.get()

    def checkinDownloader_(self, downloader):
        if not downloader.hasStarted:
            self.createDownloader_()
        else:
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
            callbackTakingString(readAtLeast(fileDescriptor, sz))

        self.executeAndCallbackWithFileDescriptor(toExecute,
                                                  callbackTakingFDAndSize,
                                                  inputCallback)


def main(argv):
    runner = OutOfProcessDownloader(True, socket.fromfd(int(argv[1]), socket.AF_UNIX, 0))
    runner.executeChild_()

if __name__ == '__main__':
    import ufora.config.Setup as Setup

    setup = Setup.defaultSetup()

    setup.config.configureLogging(logging.INFO)

    with Setup.PushSetup(setup):
        main(sys.argv)



