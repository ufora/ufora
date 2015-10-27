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

import threading
import unittest
from ufora.util.ThreadLocalStack import ThreadLocalStack

class TestThreadLocalStack(unittest.TestCase):

    def test_create(self):
        tls = ThreadLocalStack()

    def test_push(self):
        tls = ThreadLocalStack()
        toPush = 'value'
        tls.push(toPush)
        self.assertEqual(tls.top, toPush)

    def test_pop(self):
        tls = ThreadLocalStack()
        tls.push('value')
        self.assertEqual(tls.pop(), 0)

    def test_multiplePush(self):
        tls = ThreadLocalStack()
        tls.push('value1')
        tls.push('value2')

        self.assertEqual(tls.top, 'value2')
        self.assertEqual(tls.pop(), 1)
        self.assertEqual(tls.top, 'value1')
        self.assertEqual(tls.pop(), 0)


    def test_popWithoutPush(self):
        tls = ThreadLocalStack()
        with self.assertRaises(AssertionError):
            tls.pop()

    def test_topWithoutPush(self):
        tls = ThreadLocalStack()
        with self.assertRaises(AssertionError):
            x = tls.top

    def test_popOnDifferentThread(self):
        tls = ThreadLocalStack()
        tls.push('value')

        def popThread():
            with self.assertRaises(AssertionError):
                tls.pop()

        thread = threading.Thread(target = popThread)
        thread.start()
        thread.join()

