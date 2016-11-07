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

import time
import threading

from ufora.BackendGateway.SubscribableWebObjects.SubscribableObject \
    import SubscribableObject, ExposedProperty, ExposedFunction

class TestSubscribable(SubscribableObject):
    def __init__(self, id, cumulus_env, args):
        super(TestSubscribable, self).__init__(id, cumulus_env)
        self.definition = args['definition']
        self._aValue = 0


    @ExposedProperty
    def aValue(self):
        return self._aValue


    @ExposedFunction
    def set_aValue(self, value):
        self._aValue = value


    @ExposedProperty
    def depth(self):
        if isinstance(self.definition, list):
            res = 0
            for x in self.definition:
                res += x.depth
            return res
        else:
            return 0


    def anUnexposedFunction(self, jsonArg):
        self.aValue = jsonArg


    @ExposedFunction
    def testFunction(self, arg):
        return arg

