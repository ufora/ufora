#   Copyright 2016 Ufora Inc.
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


"""Pure Python Implementations of Python builtins (in alphabetical order)."""

import pyfora.PureImplementationMapping as PureImplementationMapping
from pyfora.PureImplementationMapping import pureMapping
import time


@pureMapping(time.time)
class Time(object):
    def __call__(self):
        return __inline_fora(
            """fun(@unnamed_args:(), @named_args: (), *args) {
                  return PyFloat(cached`(#Time()))
                  }"""
            )()

