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

"""A Python client for Ufora

The ``pyfora`` package makes it easy to connect to a Ufora cluster, submit
arbitrary computations to the cluster in the form of "Pure Python" code the result
back into Python.


Pure (for "purely functional") Python, is a subset of python in which:

- All data structures are immutable (e.g. no modification of lists)
- Operations have no side-effects (e.g. no access to files or print functions)
- Operations are deterministic  (e.g. no access to system time)

"""



from pyfora._version import __version__

from pyfora.Connection import connect
from pyfora.Exceptions import *
