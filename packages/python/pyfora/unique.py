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

def filterWithIndex(vec, f, lowIndex=0, highIndex=None, depth=0):
    if highIndex is None:
        highIndex = len(vec)

    if highIndex < 0:
        highIndex = highIndex + len(vec)

    if lowIndex < 0:
        lowIndex = lowIndex + len(vec)

    if lowIndex == highIndex:
        return []

    if lowIndex + 1 == highIndex or depth > 10:
        tr = []
        while lowIndex < highIndex:
            if f(vec, lowIndex):
                tr = tr + [vec[lowIndex]]

            lowIndex = lowIndex + 1

        return tr

    mid = (lowIndex + highIndex) / 2

    return filterWithIndex(vec, f, lowIndex, mid, depth + 1) + \
        filterWithIndex(vec, f, mid, highIndex, depth + 1)

def unique(vec, isSorted=False):
    # pythonic way of getting unique elements in a container is `list(set(vec))`.
    # pyfora doesn't currently support `set`
    if not isSorted:
        sortedVec = sorted(vec)
    else:
        sortedVec = vec

    return filterWithIndex(
        sortedVec,
        lambda sortedVec, ix: ix < 1 or sortedVec[ix - 1] < sortedVec[ix]
        )

