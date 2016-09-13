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

"""A simplified view into SharedState for use by the tsunami GUI"""

import logging

import ufora.util.ThreadLocalStack as ThreadLocalStack
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.native.Json as NativeJson

def getSynchronizer():
    return SharedStateSynchronizer.getCurrent()

def getView():
    return getSynchronizer().view

def isConnected():
    return getView() is not None



class SharedStateSynchronizer(ThreadLocalStack.ThreadLocalStackPushable):
    def __init__(self):
        ThreadLocalStack.ThreadLocalStackPushable.__init__(self)

        self.view_ = None
        self.listener_ = None

        #these dictionaries
        self.keyspaceListenersByKeyspaceAndPrefix_ = {}
        self.keyspaceListenersHaveHadFirstLoad_ = set()
        self.loadedKeyspacesAndPrefixes_ = set()
        self.valuesByKeyspaceAndPrefix_ = {}
        self.unwrittenValuesByKeyspaceAndPrefix_ = {}
        self.keyspaceNameToPrefixes_ = {}

        self.pendingWrites_ = []

    def __del__(self):
        if self.pendingWrites_:
            logging.critical("SharedStateSynchronizer destroyed with %s pending writes",
                             len(self.pendingWrites_))

    def addKeyspaceListener(self,
                            keyspaceName,
                            keyspaceListener,
                            keyPrefix,
                            blockUntilLoaded=False,
                            assertAlreadyLoaded=False):
        """Add a keyspace listener to the synchronizer."""
        assert isinstance(keyPrefix, NativeJson.Json)
        assert keyPrefix.isArray()

        assert isinstance(keyspaceName, NativeJson.Json)

        lookupKey = (keyspaceName, keyPrefix)

        if keyspaceName not in self.keyspaceNameToPrefixes_:
            self.keyspaceNameToPrefixes_[keyspaceName] = set()

        for otherPrefix in self.keyspaceNameToPrefixes_[keyspaceName]:
            assert not (otherPrefix.arrayStartswith(keyPrefix) and otherPrefix != keyPrefix), (
                "Can't subscribe to %s:%s since we're already subscribed to %s:%s" % (
                    keyspaceName,
                    keyPrefix,
                    keyspaceName,
                    otherPrefix
                    )
                )

        self.keyspaceNameToPrefixes_[keyspaceName].add(keyPrefix)

        if lookupKey not in self.keyspaceListenersByKeyspaceAndPrefix_:
            if assertAlreadyLoaded:
                assert False, "Keyspace %s was not already loaded." % keyspaceName

            self.keyspaceListenersByKeyspaceAndPrefix_[lookupKey] = set()
            self.keyspaceListenersByKeyspaceAndPrefix_[lookupKey].add(keyspaceListener)
            self.valuesByKeyspaceAndPrefix_[lookupKey] = {}

            logging.info("shared state subscribing to %s:%s", keyspaceName, keyPrefix)

            keyspace = SharedState.Keyspace("TakeHighestIdKeyType", keyspaceName, 1)

            self.view_.subscribe(
                SharedState.KeyRange(
                    keyspace,
                    0,
                    keyPrefix,
                    keyPrefix + NativeJson.Json([None]),
                    True,
                    False
                    ),
                blockUntilLoaded
                )

            if blockUntilLoaded:
                self.update()
                self.ensureMarkedLoaded(lookupKey)
        else:
            self.keyspaceListenersByKeyspaceAndPrefix_[lookupKey].add(keyspaceListener)

            keyspaceListener.keysLoaded(
                self.valuesByKeyspaceAndPrefix_[lookupKey],
                True
                )


    def writeValue(self, keyspaceName, keyName, value):
        assert isinstance(keyspaceName, NativeJson.Json)
        assert isinstance(keyName, NativeJson.Json)
        assert isinstance(value, NativeJson.Json)

        keyPrefix = self.prefixFor_(keyspaceName, keyName)
        assert (keyspaceName, keyPrefix) in self.keyspaceListenersByKeyspaceAndPrefix_

        if (keyspaceName, keyPrefix) not in self.loadedKeyspacesAndPrefixes_:
            if (keyspaceName, keyPrefix) not in self.unwrittenValuesByKeyspaceAndPrefix_:
                self.unwrittenValuesByKeyspaceAndPrefix_[(keyspaceName, keyPrefix)] = []
            self.unwrittenValuesByKeyspaceAndPrefix_[(keyspaceName, keyPrefix)].append(
                (keyspaceName, keyName, value)
                )
        else:
            self.pendingWrites_.append((keyspaceName, keyName, value))

    def commitPendingWrites(self):
        try:
            if self.pendingWrites_:
                for keyspaceName, keyName, value in self.pendingWrites_:
                    with self.createTransaction():
                        self.writeValue_(keyspaceName, keyName, value)

                self.pendingWrites_ = []
        except UserWarning as e:
            if e.message == 'channel disconnected':
                logging.error("SharedStateSynchronizer lost connection to shared state while "\
                "committing pending writes.")
            else:
                raise

    def writeValue_(self, keyspaceName, keyName, value):
        self.view_[SharedState.Key(
            SharedState.Keyspace("TakeHighestIdKeyType", keyspaceName, 1),
            (keyName,)
            )] = value

    @property
    def view(self):
        return self.view_

    @property
    def listener(self):
        return self.listener_

    def attachView(self, view):
        self.view_ = view
        self.listener_ = SharedState.Listener(view)

    def update(self):
        if self.isAttachedToView():
            while self.view_.isFrozen:
                assert self.view_.abort() == 0
            self.update_()

    def isAttachedToView(self):
        return self.view_ is not None

    def update_(self):
        self.updateKeysAndKeyspaces_()

    def prefixFor_(self, keyspaceName, keyName):
        if keyspaceName not in self.keyspaceNameToPrefixes_:
            assert False, "%s not in %s" % (keyspaceName, self.keyspaceNameToPrefixes_.keys())
        for prefix in self.keyspaceNameToPrefixes_[keyspaceName]:
            if keyName.arrayStartswith(prefix):
                return prefix
        assert False, "Couldn't find a prefix for %s in %s" % (
            keyName,
            self.keyspaceNameToPrefixes_[keyspaceName]
            )

    def waitForKeyspaceAndPrefix(self, keyspaceName, prefixName):
        self.update()
        while (keyspaceName, prefixName) not in self.loadedKeyspacesAndPrefixes_:
            self.listener_.wait()
            self.update()

    def isSharedStateDisconnected(self):
        return not self.listener_.isConnected

    def updateKeysAndKeyspaces_(self):
        valueDict = {}
        changedKeys = ()
        done = False

        self.commitPendingWrites()
        with self.createTransaction():
            while not done:
                done = True
                updates = self.listener_.getNonblock()

                for updateType, update in updates:
                    if updateType == "KeyUpdates":
                        changedKeys = update
                        for key in changedKeys:
                            done = False
                            keyspaceName = key.keyspace
                            keyname = key.firstKeyDimension
                            prefix = self.prefixFor_(keyspaceName, keyname)

                            lookupId = (keyspaceName, prefix)

                            if lookupId not in valueDict:
                                valueDict[lookupId] = {}

                            valueNode = self.view_[key]
                            if valueNode is not None:
                                valueDict[lookupId][keyname] = self.view_[key].value()
                    elif updateType == "SubscriptionStart":
                        #the update is a KeyRange object
                        keyspaceName = update.keyspace.name

                        if update.left() is None:
                            keyPrefix = ""
                        else:
                            keyPrefix = update.left()[0]

                        lookupId = (keyspaceName, keyPrefix)

                        if keyspaceName  not in valueDict:
                            valueDict[lookupId] = {}

                        self.loadedKeyspacesAndPrefixes_.add(lookupId)

                        if lookupId in self.unwrittenValuesByKeyspaceAndPrefix_:
                            self.pendingWrites_ += self.unwrittenValuesByKeyspaceAndPrefix_[lookupId]
                            del self.unwrittenValuesByKeyspaceAndPrefix_[lookupId]



        for keyspaceNameAndPrefix in valueDict:
            if keyspaceNameAndPrefix in self.keyspaceListenersByKeyspaceAndPrefix_:
                isFirstLoad = False
                if keyspaceNameAndPrefix not in self.keyspaceListenersHaveHadFirstLoad_:
                    isFirstLoad = True
                    self.keyspaceListenersHaveHadFirstLoad_.add(keyspaceNameAndPrefix)

                for listener in self.keyspaceListenersByKeyspaceAndPrefix_[keyspaceNameAndPrefix]:
                    listener.keysLoaded(
                        valueDict[keyspaceNameAndPrefix],
                        isFirstLoad
                        )

                self.valuesByKeyspaceAndPrefix_[keyspaceNameAndPrefix].update(
                    valueDict[keyspaceNameAndPrefix]
                    )

    def ensureMarkedLoaded(self, lookupKey):
        if lookupKey not in self.keyspaceListenersHaveHadFirstLoad_:
            self.keyspaceListenersHaveHadFirstLoad_.add(lookupKey)

            for listener in self.keyspaceListenersByKeyspaceAndPrefix_[lookupKey]:
                listener.keysLoaded({}, True)

    def createTransaction(self):
        return SharedState.Transaction(self.view_)

    def flush(self):
        while self.unwrittenValuesByKeyspaceAndPrefix_:
            for pair in self.unwrittenValuesByKeyspaceAndPrefix_:
                break
            self.waitForKeyspaceAndPrefix(pair[0], pair[1])

        self.commitPendingWrites()
        self.view_.flush()


