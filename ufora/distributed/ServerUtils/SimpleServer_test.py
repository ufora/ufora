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

import unittest
import ufora.distributed.ServerUtils.SimpleServer as SimpleServer
import threading
import ufora.config.Setup as Setup

def suppressExceptionLogging(f):
    def execute(*args, **kwds):
        try:
            return f(*args, **kwds)
        except:
            pass
    return execute

class TestSimpleServer(unittest.TestCase):
    def testDualConnectThrows(self):
        server1 = SimpleServer.SimpleServer(port = Setup.config().testPort)

        thread1 = threading.Thread(target=suppressExceptionLogging(server1.runListenLoop))
        thread1.start()
        server1.blockUntilListening()

        server2 = SimpleServer.SimpleServer(port = Setup.config().testPort)
        thread2 = threading.Thread(target=suppressExceptionLogging(server2.runListenLoop))
        thread2.start()

        self.assertRaises(Exception, server2.blockUntilListening)
        server1.stop()
        server2.stop()

        thread1.join()
        thread2.join()


    def testRapidOpenClose(self):
        for ix in range(100):
            server = SimpleServer.SimpleServer(port=Setup.config().testPort)

            thread = threading.Thread(target=suppressExceptionLogging(server.runListenLoop))
            thread.start()

            server.blockUntilListening()

            server.stop()

            thread.join()

