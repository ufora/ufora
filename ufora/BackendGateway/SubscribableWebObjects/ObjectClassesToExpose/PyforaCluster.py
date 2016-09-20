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

from ufora.BackendGateway.SubscribableWebObjects.SubscribableObject \
    import SubscribableObject, ExposedFunction



class PyforaCluster(SubscribableObject):
    def __init__(self, id, cumulus_gateway, cache_loader, _):
        super(PyforaCluster, self).__init__(id, cumulus_gateway, cache_loader)


    @ExposedFunction()
    def getClusterStatus(self, _):
        status = self.cumulus_gateway.getClusterStatus()
        return status
