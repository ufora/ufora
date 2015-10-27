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

import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness
import ufora.util.RetryAssert as RetryAssert
import ufora.native.Json as NativeJson

import unittest
import logging
import random



class IntrospectionTest(unittest.TestCase):
    def setUp(self):
        self.harness = SharedStateTestHarness.SharedStateTestHarness(True)
        self.manager = SharedStateService.KeyspaceManager(10001,1, pingInterval=1)
        self.introKeyspace = SharedState.getClientInfoKeyspace()
        self.introRange = SharedState.KeyRange(self.introKeyspace, 1, None, None, True, False)
        self.views = []
        self.maxDiff = None
    def tearDown(self):
        self.harness.teardown()

    def newView(self):
        return self.harness.newView()

    def getIntrospectionContentsForView(self, view):
        for k, v in SharedState.iterItems(view, SharedState.getClientInfoKeyspace()):
            if v.value() != NativeJson.Json('disconnected'):
                yield int(k[1].toSimple())

    def getIntrospectionTable(self, views):
        tr = {}
        for v in views:
            with SharedState.Transaction(v):
                tr[v.id] = set(i for i in self.getIntrospectionContentsForView(v))
        return tr

    def getExpectedFromViewList(self, views):
        return dict((v.id, set(v.id for v in views)) for v in views)

    def resizeViews(self, views, size):
        if size > len(views):
            for x in range(size - len(views)):
                v = self.newView()
                v.waitConnect()
                logging.debug('Adding: %s to the test manager list', v.id)
                v.subscribe(self.introRange)
                views.append(v)
        if size < len(views):
            for x in range(len(views) - size):
                v = views.pop()
                logging.debug('Removing: %s from the test manager list',  v.id)

    def assertDictsSame(self, dict1, dict2):
        self.assertEqual(dict1.keys(), dict2.keys())
        for d in dict1.keys():
            self.assertEqual({d:dict1[d]}, {d:dict2[d]})

    def assertExpected(self, views):
        getTable = lambda : self.getIntrospectionTable(views)
        expected = lambda : self.getExpectedFromViewList(views)
        RetryAssert.retryAssert(self.assertDictsSame, [getTable, expected], numRetries=50)

    def test_introspection_harder(self):
        views = []
        random.seed(14)
        for x in range(40):
            newSize = random.randint(1,33)
            self.resizeViews(views, newSize)
        self.assertExpected(views)


    def test_introspection_basic(self):
        views = []
        self.resizeViews(views, 4)
        self.assertExpected(views)

        self.resizeViews(views, 2)
        self.assertExpected(views)

        self.resizeViews(views, 2)
        self.assertExpected(views)

    #@attr('disabled')
    #def test_cant_push_to_introspection(self):
        #v = self.newView()
        #v.waitConnect()
        #v.subscribe(self.introRange)
        #def addTo(v):
            #with SharedState.Transaction(v):
                #print 'txtrying'
                #key = SharedState.Key(self.introKeyspace, ("0",str(v.id)))
                #v[key] = "some data"
                #self.assertTrue(v.connected)

        #addTo(v)
        #RetryAssert.retryAssert(self.assertTrue, [lambda: not v.connected], numRetries = 50)

    def test_exception(self):
        v = self.newView()
        v.waitConnect()
        v.subscribe(self.introRange)

        key = SharedState.Key(self.introKeyspace, (NativeJson.Json("0"),NativeJson.Json(str(v.id))))
        # this should raise because the view is not frozen
        def shouldRaise():
            v[key] = NativeJson.Json("some data")
        self.assertRaises(UserWarning, shouldRaise)

