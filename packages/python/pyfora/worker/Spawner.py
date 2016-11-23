#   Copyright 2016 Ufora Inc.
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

import time
import os
import socket
import sys
import logging
import traceback
import threading

import pyfora.worker.worker as worker
import pyfora.worker.Worker as Worker
import pyfora.worker.Common as Common
import pyfora.worker.Messages as Messages
import pyfora.worker.SubprocessRunner as SubprocessRunner

class WorkerConnectionBase:
    def __init__(self, socket_name, socket_dir):
        self.socket_name = socket_name
        self.socket_dir = socket_dir

    def answers_self_test(self, logErrors = False):
        sock = None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(os.path.join(self.socket_dir, self.socket_name))

            Common.writeAllToFd(sock.fileno(), Messages.MSG_TEST)
            Common.writeString(sock.fileno(), "msg")
            return Common.readString(sock.fileno()) == "msg"
        except:
            if logErrors:
                logging.error("Failed to answer self-test: %s", traceback.format_exc())
            return False
        finally:
            try:
                sock.close()
            except:
                pass

    def teardown(self):
        self.shutdown_worker()
        self.remove_socket()

    def remove_socket(self):
        try:
            os.unlink(os.path.join(self.socket_dir, self.socket_name))
        except OSError:
            pass

    def shutdown_worker(self):
        raise NotImplementedError("Subclasses implement")

    def processLooksTerminated(self):
        raise NotImplementedError("Subclasses implement")

    def cleanupAfterAppearingDead(self):
        raise NotImplementedError("Subclasses implement")

class OutOfProcessWorkerConnection(WorkerConnectionBase):
    def __init__(self, socket_name, socket_dir):
        WorkerConnectionBase.__init__(self, socket_name, socket_dir)

        worker_socket_path = os.path.join(socket_dir, socket_name)

        logging.error("socket path: %s", worker_socket_path)

        def onStdout(msg):
            logging.info("%s/%s out> %s", socket_dir, socket_name, msg)

        def onStderr(msg):
            logging.info("%s/%s err> %s", socket_dir, socket_name, msg)

        pid = os.fork()

        if pid == 0:
            #we are the child
            try:
                code = Worker.Worker(worker_socket_path).executeLoop()
            except:
                logging.error("worker had exception")
                code = 1

            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(code)
        else:
            self.childpid = pid

    def shutdown_worker(self):
        os.kill(self.childpid, 9)
        os.waitpid(self.childpid, 0)

    def processLooksTerminated(self):
        pid,exit = os.waitpid(self.childpid, os.WNOHANG)
        return pid == self.childpid

    def cleanupAfterAppearingDead(self):
        #this worker is dead!
        logging.info("worker %s/%s was busy but looks dead to us", self.socket_dir, self.socket_name)
        self.remove_socket()

class InProcessWorkerConnection(WorkerConnectionBase):
    def __init__(self, socket_name, socket_dir):
        WorkerConnectionBase.__init__(self, socket_name, socket_dir)

        worker_socket_path = os.path.join(socket_dir, socket_name)

        worker = Worker.Worker(worker_socket_path)

        self.thread = threading.Thread(target=worker.executeLoop, args=())
        self.thread.start()

    def shutdown_worker(self):
        self.send_shutdown_message()
        self.thread.join()

    def send_shutdown_message(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(os.path.join(self.socket_dir, self.socket_name))

            Common.writeAllToFd(sock.fileno(), Messages.MSG_SHUTDOWN)
            return True
        except:
            logging.error("Couldn't communicate with %s/%s:\n%s", self.socket_dir, self.socket_name, traceback.format_exc())
            return False
        finally:
            try:
                sock.close()
            except:
                pass

    def processLooksTerminated(self):
        return False

    def cleanupAfterAppearingDead(self):
        raise UserWarning("This function makes no sense on an in-process worker")

class Spawner:
    def __init__(self, socket_dir, selector_name, max_processes, outOfProcess):
        self.outOfProcess = outOfProcess
        self.workerType = OutOfProcessWorkerConnection if outOfProcess else InProcessWorkerConnection

        self.selector_name = selector_name
        self.socket_dir = socket_dir
        self.max_processes = max_processes

        self.selector_socket_path = os.path.join(socket_dir, selector_name)

        self.busy_workers = []
        self.waiting_workers = []

        self.waiting_sockets = []

        self.index = 0

    def clearPath(self):
        # Make sure the socket does not already exist
        try:
            os.unlink(self.selector_socket_path)
        except OSError:
            if os.path.exists(self.selector_socket_path):
                raise UserWarning("Couldn't clear named socket at %s", self.selector_socket_path)

    def teardown(self):
        self.clearPath()

    def start_worker(self):
        index = self.index
        self.index += 1

        worker_name = "worker_%s" % index
        worker_socket_path = os.path.join(self.socket_dir, worker_name)

        newWorker = self.workerType(worker_name, self.socket_dir)

        t0 = time.time()
        TIMEOUT = 10
        delay = 0.001
        while not newWorker.answers_self_test() and time.time() - t0 < TIMEOUT:
            time.sleep(delay)
            delay *= 2

        if not newWorker.answers_self_test(True):
            raise UserWarning("Couldn't start another worker after " + str(time.time() - t0))
        else:
            self.waiting_workers.append(newWorker)

            logging.info(
                "Started worker %s/%s with %s busy and %s idle", 
                self.socket_dir, 
                worker_name, 
                len(self.busy_workers), 
                len(self.waiting_workers)
                )

    def terminate_workers(self):
        for w in self.busy_workers + self.waiting_workers:
            w.teardown()

    def can_start_worker(self):
        return self.max_processes is None or len(self.busy_workers) < self.max_processes

    def get_valid_worker(self):
        while True:
            if not self.waiting_workers and self.can_start_worker():
                self.start_worker()
            elif self.waiting_workers:
                #if we have one, use it
                worker = self.waiting_workers.pop(0)

                #make sure the worker is happy
                if not worker.answers_self_test():
                    logging.error("Worker %s appears dead. Removing it.", worker.socket_name)
                    worker.teardown()
                else:
                    return worker
            else:
                if not self.check_all_busy_workers():
                    return None

    def check_all_busy_workers(self):
        new_busy = []

        for worker in self.busy_workers:
            if worker.processLooksTerminated():
                worker.cleanupAfterAppearingDead()
            else:
                new_busy.append(worker)

        if len(new_busy) != len(self.busy_workers):
            self.busy_workers = new_busy

            logging.info("Now, we have %s busy and %s idle workers", len(self.busy_workers), len(self.waiting_workers))
            return True
        return False

    def apply_worker_to_waiting_socket(self, worker):
        self.busy_workers.append(worker)
        waiting_connection = self.waiting_sockets.pop(0)

        Common.writeString(waiting_connection.fileno(), worker.socket_name)
        waiting_connection.close()

    def start_workers_if_necessary(self):
        self.check_all_busy_workers()
        
        while self.waiting_sockets and self.can_start_worker():
            worker = self.get_valid_worker()
            assert worker is not None
            self.apply_worker_to_waiting_socket(worker)

    def listen(self):
        logging.info("Setting up listening on %s with max_processes=%s", self.selector_socket_path, self.max_processes)
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self.selector_socket_path)
        sock.listen(100)

        try:
            while True:
                sock.settimeout(.1)
                connection = None

                try:
                    connection, _ = sock.accept()
                except socket.timeout as e:
                    pass

                if connection is not None:
                    if self.handleConnection(connection):
                        self.clearPath()
                        return
                    self.start_workers_if_necessary()


        except KeyboardInterrupt:
            logging.info("shutting down due to keyboard interrupt")
            self.terminate_workers()
        finally:
            sock.close()

    def handleConnection(self, connection):
        first_byte = Common.readAtLeast(connection.fileno(), 1)
        
        if first_byte == Messages.MSG_SHUTDOWN:
            logging.info("Received termination message with %s busy and %s waiting workers", len(self.busy_workers), len(self.waiting_workers))
            self.terminate_workers()
            logging.info("workers terminating. Shutting down.")
            connection.close()

            return True
        elif first_byte == Messages.MSG_GET_WORKER:
            #try to start a worker
            worker = self.get_valid_worker()

            if worker is not None:
                self.busy_workers.append(worker)

                Common.writeString(connection.fileno(), worker.socket_name)
                connection.close()
            else:
                #otherwise wait for one to come available
                self.waiting_sockets.append(connection)

            self.start_workers_if_necessary()

        elif first_byte in (Messages.MSG_RELEASE_WORKER, Messages.MSG_TERMINATE_WORKER):
            wantsTerminate = first_byte == Messages.MSG_TERMINATE_WORKER

            worker_name = Common.readString(connection.fileno())
            worker_ix = [ix for ix,w in enumerate(self.busy_workers) if w.socket_name == worker_name][0]

            worker = self.busy_workers[worker_ix]
            self.busy_workers.pop(worker_ix)

            connection.close()

            if wantsTerminate:
                worker.teardown()
            elif worker.answers_self_test():
                #see if anybody wants to use this worker
                if self.waiting_sockets:
                    self.apply_worker_to_waiting_socket(worker)
                else:
                    self.waiting_workers.append(worker)
            else:
                logging.error("Worker %s appears dead. Removing it.", worker.socket_name)
                worker.teardown()

        elif first_byte == Messages.MSG_TERMINATE_WORKER:
            worker_name = Common.readString(connection.fileno())
            worker_ix = [ix for ix,w in enumerate(self.busy_workers) if w.socket_name == worker_name][0]

            worker = self.busy_workers[worker_ix]
            self.busy_workers.pop(worker_ix)

            connection.close()

            if worker.answers_self_test():
                #see if anybody wants to use this worker
                if self.waiting_sockets:
                    self.apply_worker_to_waiting_socket(worker)
                else:
                    self.waiting_workers.append(worker)
            else:
                logging.error("Worker %s appears dead. Removing it.", worker.socket_name)
                worker.teardown()

        else:
            assert False, "unknown byte: " + first_byte
            



