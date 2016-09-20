#   Copyright 2015-2016 Ufora Inc.
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

import ufora.BackendGateway.SubscribableWebObjects.SubscribableObject as SubscribableObject


class Subscribable(SubscribableObject.SubscribableObject):
    def __init__(self, id, cumulus_gateway, cache_loader, _):
        super(Subscribable, self).__init__(id, cumulus_gateway, cache_loader)


    @SubscribableObject.ExposedFunction
    def naked_decorator(self):
        pass

    @SubscribableObject.ExposedFunction(expandArgs=True)
    def func_decorator(self):
        pass

    def undecorated(self):
        pass

    @SubscribableObject.ExposedProperty
    def prop(self):
        return 1


class TestSubscribableObject(unittest.TestCase):
    def test_is_exposed_naked_decorator(self):
        self.assertTrue(SubscribableObject.isFunctionToExpose(Subscribable.naked_decorator))

    def test_is_exposed_func_decorator(self):
        self.assertTrue(SubscribableObject.isFunctionToExpose(Subscribable.func_decorator))

    def test_decorator_args(self):
        self.assertTrue(SubscribableObject.functionExpectsExpandedArgs(Subscribable.func_decorator))

    def test_undecorated(self):
        self.assertFalse(SubscribableObject.isFunctionToExpose(Subscribable.undecorated))

    def test_exposed_property(self):
        self.assertTrue(SubscribableObject.isPropertyToExpose(Subscribable.prop))
        s = Subscribable(1, None, None, None)
        self.assertEqual(s.prop, 1)
