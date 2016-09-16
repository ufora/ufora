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

from ufora.BackendGateway.Observable import Observable, observable


class Foo(Observable):
    def __init__(self, id):
        super(Foo, self).__init__(id)
        self._value = None
        self.foo = 1


    @property
    def value(self):
        return self._value


    @value.setter
    @observable
    def value(self, value):
        self._value = value


    @observable
    def set_foo(self, foo):
        self.foo = foo



class TestObservable(unittest.TestCase):
    def test_observe_property(self):
        obj_id = 1
        value_to_set = 2
        f = Foo(obj_id)

        observed = [False]
        def observer(id, name, new_value, old_value):
            self.assertEqual(id, obj_id)
            self.assertEqual(name, 'value')
            self.assertEqual(new_value, value_to_set)
            self.assertIsNone(old_value)
            observed[0] = [True]

        f.observe('value', observer)
        f.value = value_to_set
        self.assertTrue(observed[0])


    def test_observe_method(self):
        obj_id = 2
        value_to_set = 3
        f = Foo(obj_id)

        observed = [False]
        def observer(id, name, new_value, old_value):
            self.assertEqual(id, obj_id)
            self.assertEqual(name, 'foo')
            self.assertEqual(new_value, value_to_set)
            self.assertEqual(old_value, 1)
            observed[0] = True

        f.observe('foo', observer)
        f.set_foo(value_to_set)
        self.assertTrue(observed[0])


    def test_multiple_observations(self):
        obj_id = 3
        values_to_set = [4, 5]
        previous_value = None
        f = Foo(obj_id)

        observations = [0]

        def observer(id, name, new_value, old_value):
            current_observation = observations[0]
            self.assertEqual(id, obj_id)
            self.assertEqual(name, 'value')
            self.assertEqual(new_value, values_to_set[current_observation])
            self.assertEqual(
                old_value,
                (None if current_observation == 0
                 else values_to_set[current_observation-1])
                )
            observations[0] += 1

        f.observe('value', observer)
        for v in values_to_set:
            f.value = v

        self.assertEqual(observations[0], len(values_to_set))


    def test_unobserve(self):
        obj_id = 4
        value_to_set = 5
        f = Foo(obj_id)

        observations = [0]
        def observer(id, name, new_value, old_value):
            observations[0] += 1

        f.observe('value', observer)
        f.value = value_to_set

        f.unobserve('value', observer)
        f.value = value_to_set + 1

        self.assertEqual(observations[0], 1)
