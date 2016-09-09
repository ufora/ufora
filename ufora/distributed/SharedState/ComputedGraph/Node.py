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

""" ComputedGraphSharedState

provides a very simple computed graph wrapper around shared state.

"""

import logging
import traceback


import ufora.native.Json as NativeJson
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.core.JsonPickle as JsonPickle


import ufora.distributed.SharedState.ComputedGraph.SynchronousPropertyAccess as SynchronousPropertyAccess
import ufora.distributed.SharedState.ComputedGraph.SharedStateSynchronizer as SharedStateSynchronizer
import ufora.BackendGateway.control.Control as Control


class NotLoadedException(Exception):
    def __init__(self, keyspace):
        Exception.__init__(self)
        self.keyspace = keyspace

    def __str__(self):
        return "NotLoadedException(%s)" % self.keyspace

def keyPathToKeyName(path):
    return NativeJson.Json(('CGSS', JsonPickle.toJson(path)))

class KeyspaceUpdater:
    def __init__(self, keyspace):
        self.keyspace = keyspace

    def keysLoaded(self, keyValueDict, isInitialLoad):
        for key in keyValueDict:
            if key.isArray() and len(key) == 2 and key[0] == NativeJson.Json("CGSS"):
                try:
                    keyPath = JsonPickle.fromJson(key[1])
                except:
                    import traceback

                    logging.warn(
                        "Bad key encountered in KeyspaceUpdater for keyspace %s: %s\n%s",
                        self.keyspace,
                        key,
                        traceback.format_exc()
                        )

                    #skip this key
                    continue

                node = Subspace(keyspace = self.keyspace, keyPath = keyPath)
                val = keyValueDict[key]

                if val is None:
                    node.value_ = None
                else:
                    try:
                        node.value_ = (JsonPickle.fromJson(val),)
                    except:
                        import traceback
                        traceback.print_exc()
                        logging.warn("ComputedGraphSharedState loaded bad node value at %s, %s: %s",
                            self.keyspace,
                            key,
                            repr(val)
                            )
            # else:
            #     print "ignoring ", key

        if isInitialLoad:
            self.keyspace.markLoaded()

def isTuple(value):
    if not isinstance(value, tuple):
        return False
    return True

def keyspacePathToKeyspaceName(keyspacePath):
    return NativeJson.Json([JsonPickle.toSimple(x) for x in keyspacePath])

class Keyspace(ComputedGraph.Location):
    keyspacePath = ComputedGraph.Key(object, validator=isTuple)
    isLoaded_ = ComputedGraph.Mutable(object, lambda: False)
    toCallOnLoad_ = ComputedGraph.Mutable(object, lambda: ())
    isSubscribed_ = ComputedGraph.Mutable(object, lambda: False)

    @ComputedGraph.Function
    def onLoad(self, toCallOnLoad):
        if self.isLoaded_:
            toCallOnLoad()
        else:
            if SynchronousPropertyAccess.SynchronousPropertyAccess.getCurrent() is not None:
                self.waitLoaded()
                toCallOnLoad()
                return
            else:
                self.toCallOnLoad_ = self.toCallOnLoad_ + (toCallOnLoad,)
                self.ensureSubscribed()

    def keyspaceName(self):
        return keyspacePathToKeyspaceName(self.keyspacePath)

    @ComputedGraph.Function
    def __str__(self):
        return "Keyspace(%s)" % (self.keyspacePath,)

    @ComputedGraph.Function
    def ensureSubscribed(self):
        assert SharedStateSynchronizer.isConnected()
        if not self.isSubscribed_:
            logging.info("ComputedGraphSharedState subscribing to: %s", self)

            SharedStateSynchronizer.getSynchronizer().addKeyspaceListener(
                self.keyspaceName,
                KeyspaceUpdater(self),
                NativeJson.Json(())
                )
            self.isSubscribed_ = True


    @ComputedGraph.Function
    def markLoaded(self):
        if self.isLoaded_:
            return

        logging.info("ComputedGraphSharedState marking loaded: %s", self)
        self.isLoaded_ = True
        self.ensureSubscribed()
        for toCallOnLoad in self.toCallOnLoad_:
            toCallOnLoad()
        self.toCallOnLoad_ = ()

    @ComputedGraph.Function
    def waitLoaded(self):
        if not self.isLoaded_:
            self.ensureSubscribed()
            SharedStateSynchronizer.getSynchronizer().waitForKeyspaceAndPrefix(
                                                                self.keyspaceName,
                                                                NativeJson.Json(())
                                                                )

    def loaded(self):
        if (not self.isLoaded_ and
                    SynchronousPropertyAccess.SynchronousPropertyAccess.getCurrent() is not None):
            self.ensureSubscribed()
            self.waitLoaded()
            return True
        else:
            self.ensureSubscribed()
            return self.isLoaded_

    def subspace(self):
        return Subspace(keyspace = self, keyPath = ())

    @ComputedGraph.Function
    def subKeyspace(self, subspaceName):
        return Keyspace(keyspacePath=self.keyspacePath + (subspaceName,))

    @ComputedGraph.Function
    def assertLoaded(self):
        if not self.loaded:
            raise NotLoadedException(self)



class Subspace(ComputedGraph.Location):
    keyspace = object
    keyPath = ComputedGraph.Key(object, validator=isTuple)
    value_ = ComputedGraph.Mutable(object, lambda: None)

    def keyName(self):
        return NativeJson.Json(('CGSS',JsonPickle.toJson(self.keyPath)))

    def loaded(self):
        return self.keyspace.loaded

    @ComputedGraph.Function
    def subKeyspace(self, subKeyspaceName):
        return Subspace(
            keyspace = self.keyspace.subKeyspace(subKeyspaceName),
            keyPath = self.keyPath
            )

    @ComputedGraph.Function
    def subspace(self, subspace):
        return Subspace(
            keyspace = self.keyspace,
            keyPath = self.keyPath + (subspace,)
            )

    @ComputedGraph.Function
    def __str__(self):
        return "Subspace(%s,%s)" % (self.keyspace, self.keyPath)

    @ComputedGraph.Function
    def setValueSlot(self, newValue):
        logging.info("Setting %s %s", str(self), newValue)
        if not self.keyspace.loaded:
            if SynchronousPropertyAccess.SynchronousPropertyAccess.getCurrent() is not None:
                self.keyspace.waitLoaded()
            else:
                logging.info("raising NotLoadedException for %s", self)
                raise NotLoadedException(self.keyspace)

        if newValue is None:
            SharedStateSynchronizer.getSynchronizer().writeValue(
                self.keyspace.keyspaceName,
                self.keyName,
                None
                )
        else:
            assert isinstance(newValue, tuple)
            assert len(newValue) == 1

            try:
                SharedStateSynchronizer.getSynchronizer().writeValue(
                    self.keyspace.keyspaceName,
                    self.keyName,
                    JsonPickle.toJson(newValue[0])
                    )
            except Exception as e:
                logging.error("%s", traceback.format_exc())
                raise

        self.value_ = newValue

    @ComputedGraph.WithSetter(setValueSlot)
    def value(self):
        if not self.keyspace.loaded:
            if SynchronousPropertyAccess.SynchronousPropertyAccess.getCurrent() is not None:
                self.keyspace.waitLoaded()
            else:
                logging.info("raising NotLoadedException for %s", self)
                raise NotLoadedException(self.keyspace)

        return self.value_




