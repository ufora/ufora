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


"""DownloadPolicy

Policy objects that allow us to describe which pyfora values we want to 
pull into the local python instance from the server when using the 
WithBlockExecutor.
"""

import pyfora.Exceptions as Exceptions

class DownloadPolicy(object):
    """Implements a two-phase model for downloading objects from the server.

    In the first phase (instantiatePolicyCheck), policies may check whether 
    they wish to download a value and trigger it if so. They return a handle 
    that will be passed back to them in the second phase.

    In the second phase (resolveToFinalValue), the handle is passed back to them
    and they must determine the final value for the variable.
    """
    def initiatePolicyCheck(self, varname, remoteObject):
        """Take a variable pair and return an handle that will be passed back to us."""
        raise NotImplementedError()

    def resolveToFinalValue(self, policyInstance):
        """Resolve a handle to the value that this variable will take in a With block.."""
        raise NotImplementedError()

class DownloadAllPolicy(DownloadPolicy):
    def initiatePolicyCheck(self, varname, remoteObject):
        return remoteObject.toLocal()

    def resolveToFinalValue(self, remoteObjectFuture):
        return remoteObjectFuture.result()

class DownloadNonePolicy(DownloadPolicy):
    def initiatePolicyCheck(self, varname, remoteObject):
        return remoteObject

    def resolveToFinalValue(self, remoteObject):
        return remoteObject

class DownloadSmallPolicy(DownloadPolicy):
    def __init__(self, maxBytecount):
        self.maxBytecount = maxBytecount

    def initiatePolicyCheck(self, varname, remoteObject):
        return {'remote': remoteObject, 'future': remoteObject.toLocal(self.maxBytecount)}

    def resolveToFinalValue(self, remoteAndFuture):
        remote, future = remoteAndFuture['remote'], remoteAndFuture['future']

        if future.exception() is not None and \
                isinstance(future.exception(), Exceptions.ResultExceededBytecountThreshold):
            return remote

        return future.result()

