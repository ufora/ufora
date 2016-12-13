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

import ufora
import ufora.config.Setup as Setup

from pyfora.Exceptions import ConnectionError
import pyfora.SocketIoJsonInterface as SocketIoJsonInterface
import pyfora.SubscribableWebObjects as SubscribableWebObjects
import ufora.test.ClusterSimulation as ClusterSimulation




class EventHandler(object):
    def __init__(self, event=None, onSuccess=None, onFailure=None, onChanged=None):
        self._event = event
        self._onSuccess = onSuccess
        self._onFailure = onFailure
        self._onChanged = onChanged
        self.responses = {
            'Success': [],
            'Failure': [],
            'Changed': []
            }

    def _onCallback(self, name, value):
        self.responses[name].append(value)
        if self._event:
            self._event.set()
        callback = getattr(self, "_on"+name)
        if callback:
            callback(value)

    def onSuccess(self, response):
        self._onCallback('Success', response)

    def onFailure(self, response):
        self._onCallback('Failure', response)

    def onChanged(self, response):
        self._onCallback('Changed', response)

class TestSubscribableWebObjects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import logging
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.basicConfig(level=logging.DEBUG)

        cls.config = Setup.config()
        cls.simulation = ClusterSimulation.Simulator.createGlobalSimulator()
        cls.simulation.startService()

    @classmethod
    def tearDownClass(cls):
        cls.simulation.stopService()


    @classmethod
    def createInterface(cls, events=None, version=None):
        return SocketIoJsonInterface.SocketIoJsonInterface(
            'http://localhost:30000',
            '/subscribableWebObjects',
            events=events,
            version=version
            )


    def connect(self, events=None, version=None):
        interface = self.createInterface(events, version)
        interface.connect()
        return interface


    def assertSuccessResponse(self, eventHandler):
        self.assertEqual(len(eventHandler.responses['Success']), 1, eventHandler.responses)
        self.assertEqual(len(eventHandler.responses['Failure']), 0, eventHandler.responses)
        self.assertEqual(len(eventHandler.responses['Changed']), 0, eventHandler.responses)


    def test_version_mismatch(self):
        interface = self.createInterface(version="0.0")
        with self.assertRaises(ConnectionError):
            interface.connect()


    def test_computed_graph_function_invocation_returns_its_argument(self):
        event = threading.Event()
        interface = self.connect()
        webObjects = SubscribableWebObjects.WebObjectFactory(interface, maxObjectIds=10)
        testSubscribable = webObjects.TestSubscribable({'definition': 0})
        eventHandler = EventHandler(event)
        inputArg = "test argument"
        testSubscribable.testFunction(inputArg, eventHandler)
        event.wait()
        self.assertSuccessResponse(eventHandler)
        response = eventHandler.responses['Success'][0]
        self.assertTrue(response == inputArg)
        interface.close()


    def test_failure_callback(self):
        event = threading.Event()

        interface = self.connect()
        webObjects = SubscribableWebObjects.WebObjectFactory(interface, maxObjectIds=10)
        testSubscribable = webObjects.TestSubscribable({'this_should_fail': 0})
        eventHandler = EventHandler(event)
        testSubscribable.get_aValue(eventHandler)
        event.wait()

        self.assertEqual(len(eventHandler.responses['Success']), 0)
        self.assertEqual(len(eventHandler.responses['Failure']), 1)
        self.assertEqual(len(eventHandler.responses['Changed']), 0)
        failure = eventHandler.responses['Failure'][0]
        self.assertIn('responseType', failure)
        self.assertEqual(failure['responseType'], 'Exception')

        interface.close()


    def test_connect_repeatedly(self):
        for i in xrange(10):
            event = threading.Event()

            interface = self.connect()

            webObjects = SubscribableWebObjects.WebObjectFactory(interface, maxObjectIds=10)
            testSubscribable = webObjects.TestSubscribable({'definition': i})

            eventHandler = EventHandler(event)
            testSubscribable.get_aValue(eventHandler)
            event.wait()

            self.assertSuccessResponse(eventHandler)
            response = eventHandler.responses['Success'][0]
            self.assertEqual(response, 0)

            interface.close()

    def test_multi_threaded_access(self):
        threadCount = 5
        iterations = 10
        threadResults = [None] * threadCount

        def threadProc(ix, iterations):
            for i in xrange(iterations):
                event = threading.Event()

                interface = self.connect()

                webObjects = SubscribableWebObjects.WebObjectFactory(interface, maxObjectIds=10)
                testSubscribable = webObjects.TestSubscribable({'definition': ix*iterations + i})

                eventHandler = EventHandler(event)
                testSubscribable.get_aValue(eventHandler)
                event.wait()

                for eventType in ['Failure', 'Changed']:
                    if len(eventHandler.responses[eventType]) > 0:
                        threadResults[ix] = eventHandler.responses[eventType]
                        break

                if threadResults[ix] is None:
                    threadResults[ix] = eventHandler.responses['Success'][0]

                interface.close()

        threads = [threading.Thread(target=threadProc, args=(ix, iterations))
                   for ix in xrange(threadCount)]
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertTrue(
            all([res == 0 for res in threadResults]),
            threadResults
            )

    def disabled_volumeTest(self):
        interface = self.connect()
        webObjects = SubscribableWebObjects.WebObjectFactory(interface, maxObjectIds=50)
        initialTimesCleared = webObjects.sessionState.timesCleared

        totalToTry = 11000
        maxToSubmitAtOnce = 1000
        totalSubmitted = [0]
        totalReceived = [0]

        allDone = threading.Event()

        def receivedAll():
            return totalReceived[0] == totalToTry

        def canSubmit():
            return (
                totalSubmitted[0] < totalToTry and
                totalSubmitted[0] - totalReceived[0] < maxToSubmitAtOnce)

        def submitOne():
            #if totalSubmitted[0] % 100 == 0:
                #print "submitting definition:", totalSubmitted[0]
            def onValue(value):
                totalReceived[0] += 1
                #if totalReceived[0] % 100 == 0:
                    #print "total received:", totalReceived[0]
                if receivedAll():
                    allDone.set()
                elif canSubmit():
                    submitOne()

            loc = webObjects.TestSubscribable({'definition': totalSubmitted[0]})
            loc.get_aValue(EventHandler(onSuccess=onValue))
            totalSubmitted[0] += 1

        while canSubmit():
            submitOne()

        allDone.wait()
        self.assertGreater(webObjects.sessionState.timesCleared,
                           initialTimesCleared)


if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])

