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
import ufora.native.TCMalloc as TCMallocNative
import threading
import Queue

def memoryFreeingThreadLoop(queue):
    while True:
        element = queue.get()

        if element == "exit":
            return

        address, event = element

        TCMallocNative.freeAtAddress(address)

        event.set()


class ComponentModelTest(unittest.TestCase):
    def test_allocInOneThreadAndDeallocateInAnother(self):
        queue = Queue.Queue()

        thread = threading.Thread(target=memoryFreeingThreadLoop, args=(queue,))
        thread.start()

        #allocate 100 GB and free in the other thread
        for ix in range(1000):
            event = threading.Event()
            address = TCMallocNative.mallocAndReturnAddress(100 * 1024 * 1024)

            queue.put((address, event))

            event.wait()

        queue.put("exit")

        thread.join()

    def test_realloc(self):
        #verify that TCMalloc accounts for resizing correctly
        measurements = [TCMallocNative.getBytesUsed()]

        for ix in range(10):
            addr = TCMallocNative.mallocAndReturnAddress(10 * 1024 * 1024)
            addr = TCMallocNative.reallocAtAddress(addr, 20 * 1024 * 1024)
            measurements.append(TCMallocNative.getBytesUsed())
            addr = TCMallocNative.reallocAtAddress(addr, 10 * 1024 * 1024)
            addr = TCMallocNative.reallocAtAddress(addr, 5 * 1024 * 1024)
            TCMallocNative.freeAtAddress(addr)

            measurements.append(TCMallocNative.getBytesUsed())

        self.assertTrue(
            measurements[-1] < measurements[0] + 10 * 1024 * 1024,
            "Expected %s to be less than 10 MB larger than %s" % (measurements[-1], measurements[0])
            )

    def test_strings(self):
        bytes = TCMallocNative.getBytesUsed()
        for ix in range(100):
            s = str(ix) * 1000000
            s2 = TCMallocNative.returnStringArg(s)
            self.assertEqual(s, s2)
        finalBytes = TCMallocNative.getBytesUsed()
        self.assertTrue(finalBytes < bytes + 10000000)

