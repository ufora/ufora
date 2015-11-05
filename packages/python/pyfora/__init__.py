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

"""
The Pyfora Client


The pyfora package makes it easy to connect to a Ufora cluster, submit 
arbitrary computations to the cluster in the form of "Pure Python" python 
code and get back a response.


Pure (for "purely function") Python, is a subset of python in which:
    - All data structures are immutable (eg: no modification of lists)
    - Operations have no side-effects (eg: no access to files or print functions)
    - Operations are deterministic  (eg: no access to system time)


pyfora.Connect() takes a url which points the pyfora client to a live Ufora 
cluster at the given IP address and port number. pyfora.Connect() returns a
pyfora.Executor object which can be used to send computations to the Ufora
cluster and get back results. 

A pyfora.Executor object is responsible for sending computations to a Ufora 
Cluster and returning the result to the client. 

pyfora.WithBlockExecutor, returned by calling `pyfora.remotely` makes it very
easy to submit a block of Python code to the cluster by wrapping that code in
a with block.

For more information about Ufora and pyfora, see:
https://ufora.github.io/ufora/

Github repo:
https://github.com/ufora/ufora

Company website:
http://www.ufora.com/
"""



from pyfora._version import __version__

from pyfora.Connection import connect
from pyfora.Exceptions import *
