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
import collections
from functools import wraps


def observable(f):
    @wraps(f)
    def wrapper(self, value):
        name = f.func_name
        if name.startswith('set_'):
            name = name[4:]
        old_value = getattr(self, name)
        f(self, value)
        self.notify(name, value, old_value)
    return wrapper


class Observable(object):
    def __init__(self, id):
        self.id = id
        self.observers = collections.defaultdict(set)


    def observe(self, name, observer):
        self.observers[name].add(observer)


    def unobserve(self, name, observer):
        self.observers[name].remove(observer)


    def notify(self, name, new_value, old_value):
        for observer in self.observers[name]:
            observer(self.id, name, new_value, old_value)

