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

import json
import ufora.util.Unicode as Unicode


class RequestError(Exception):
    pass


valid_core_counts = [0, 8, 16, 32]
valid_machine_states = ['desire', 'initializing', 'active']


def formatClusterStatus(status):
    result = {}
    for key in status.iterkeys():
        if key == 'type':
            continue
        elif key == 'remainingTime' and status[key] is not None:
            result['minutesRemaining'] = round(status[key] / 60)
        elif key in valid_machine_states:
            sizeToCount = status[key]
            for size in sizeToCount.iterkeys():
                if size != 'medium':
                    assert(sizeToCount[size] == 0)
                else:
                    result[key] = 8 * sizeToCount[size]
    return result


class CoresController(object):
    def __init__(self, transport, username):
        self.transport = transport
        self.username = username

    def set(self, numOfCores, quiet=False):
        if numOfCores not in valid_core_counts:
            raise RequestError(
                "Number of cores must be one of %s" % valid_core_counts
                )

        if not quiet:
            print "Setting number of cores to", numOfCores
        self.transport.desireMachines(numOfCores / 8, machineType='medium')

    def get(self, quiet=False):
        if not quiet:
            print 'Getting number of current cores'
        requestUri = "/cluster/users/%s" % self.username
        status, result = self.transport.submitQuery(requestUri)
        if status != 200:
            raise RequestError(status, result.content)
        return formatClusterStatus(
            json.loads(result.content, object_hook=Unicode.convertToStringRecursively)
            )

    def renew(self, quiet=False):
        if not quiet:
            print 'Renewing lease on running cores'
        currentStatus = self.get(quiet=True)
        self.set(currentStatus['desire'], quiet=True)
        return self.get(quiet=True)



