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
import threading
import ufora.native.StringChannel as StringChannelNative
import time

import ufora.native.CallbackScheduler as CallbackScheduler

callbackScheduler = CallbackScheduler.singletonForTesting()

class StringChannelTest(unittest.TestCase):
    def test_delayed_connection_workd(self):
        channel1, channel2 = StringChannelNative.InMemoryStringChannel(callbackScheduler)

        channel1Queue = channel1.makeQueuelike(callbackScheduler)

        channel1Queue.write("a")
        channel1Queue.write("b")
        channel1Queue.disconnect()

        channel2Queue = channel2.makeQueuelike(callbackScheduler)
        self.assertTrue(channel2Queue.getTimeout(1.0),"a")
        self.assertTrue(channel2Queue.getTimeout(1.0),"b")
        self.assertRaises(channel2Queue.getNonblocking)

    def test_disconnect_channel(self):
        channel1, channel2 = StringChannelNative.InMemoryStringChannel(callbackScheduler)

        channel1Queue = channel1.makeQueuelike(callbackScheduler)
        channel2Queue = channel2.makeQueuelike(callbackScheduler)

        successes = [False, False]
        def get1():
            try:
                channel1Queue.get()
            except:
                successes[0] = True

        def get2():
            try:
                channel2Queue.get()
            except:
                successes[1] = True

        thread1 = threading.Thread(target=get1)
        thread2 = threading.Thread(target=get2)
        thread1.start()
        thread2.start()

        time.sleep(.05)
        self.assertEqual(successes, [False, False])

        channel1.disconnect()

        thread1.join()
        thread2.join()

        self.assertEqual(successes, [True, True])

