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


class DummyExecutor(object):
    @property
    def remotely(self):
        return self

    def __enter__(self):
        pass

    def __exit__(self, *args):
        return True

w = 1
y = 2
def f(x):
    return x + y

class C(object):
    def __init__(self, x):
        self.x = x
    def g(self, arg):
        return self.x + arg

executor = DummyExecutor()

c = C(3)
with executor.remotely:
    z = f(w) + c.g(4) * C(5).g(6)
