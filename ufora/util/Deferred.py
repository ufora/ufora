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

class Deferred(object):
    """A simple Deferred implementation that can be used without importing twisted.
       It doesn't have the full set of features found in the twisted implementation.
    """
    def __init__(self):
        self.callbacks = []
        self.errbacks = []
        self.trigger = None

    def addCallbacks(self, callback, errback):
        self.callbacks.append(callback)
        self.errbacks.append(errback)
        if self.trigger:
            self.trigger()

    def callback(self, result):
        def trigger():
            self.runCallbacks_(result)
        self.trigger = trigger
        trigger()

    def errback(self, reason):
        def trigger():
            self.runErrbacks_(reason)
        self.trigger = trigger
        trigger()

    def runCallbacks_(self, result):
        while len(self.callbacks) > 0:
            callback = self.callbacks.pop(0)
            self.errbacks.pop(0)
            callback(result)

    def runErrbacks_(self, error):
        while len(self.errbacks) > 0:
            errback = self.errbacks.pop(0)
            self.callbacks.pop(0)
            errback(error)


class FakeDeferred(object):
    """A Deferred that fires its callback synchronously as soon as it's added.
    """
    def __init__(self, *args, **kwargs):
        self.callbackArgs = args
        self.callbackKwargs = kwargs

    def addCallbacks(self, callback, errback):
        args = self.callbackArgs or tuple()
        kwargs = self.callbackKwargs or dict()
        callback(*args, **kwargs)


