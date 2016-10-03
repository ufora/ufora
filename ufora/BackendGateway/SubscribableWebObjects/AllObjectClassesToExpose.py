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

import ufora.BackendGateway.SubscribableWebObjects.Exceptions as Exceptions

#import ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.Test as Test
import ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.PyforaObjectConverter \
    as PyforaObjectConverter
import ufora.BackendGateway.SubscribableWebObjects.Computation as Computation
#import ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.PyforaComputedValue \
    #as PyforaComputedValue
#import ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.WriteToS3Task \
    #as WriteToS3Task
import ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.PyforaCluster \
    as PyforaCluster

import ufora.BackendGateway.ComputedValue.PersistentCacheIndex as PersistentCacheIndex
import ufora.BackendGateway.ComputedValue.ViewOfEntireCumulusSystem as ViewOfEntireCumulusSystem

classMap = {
    #"Test": Test.Test,
    #"TestCGLocation": Test.TestCGLocation,
    #"ComputedValue": ComputedValue.ComputedValue,
    #"ComputedValueForMember": ComputedValue.ComputedValueForMember,
    #"ComputedValueVectorFromComputedValue": ComputedValue.ComputedValueVectorFromComputedValue,
    #"ComputedValueVectorSlice": ComputedValue.ComputedValueVectorSlice,
    #"PersistentCacheIndex": PersistentCacheIndex.PersistentCacheIndex,
    "PyforaObjectConverter": PyforaObjectConverter.PyforaObjectConverter,
    #"PyforaComputedValue": PyforaComputedValue.PyforaComputedValue,
    "Computation": Computation.Computation,
    "ViewOfEntireCumulusSystem": ViewOfEntireCumulusSystem.ViewOfEntireCumulusSystem,
    #"WriteToS3Task": WriteToS3Task.WriteToS3Task,
    #"PyforaDictionaryElement": PyforaComputedValue.PyforaDictionaryElement,
    #"PyforaTupleElement": PyforaComputedValue.PyforaTupleElement,
    #"PyforaResultAsJson": PyforaComputedValue.PyforaResultAsJson,
    "PyforaCluster": PyforaCluster.PyforaCluster
    }

def construct(json):
    if (not isinstance(json, dict) or
            'type' not in json or 'args' not in json):
        raise Exceptions.SubscribableWebObjectsException("Invalid ObjectDefinition: %s", json)

    if json['type'] not in classMap:
        raise Exceptions.SubscribableWebObjectsException("Unknown class type: %s", json['type'])

    return json['type'](json['args'])

classMapReversed_ = None
def typenameFromType(t):
    global classMapReversed_
    if classMapReversed_ is None:
        classMapReversed_ = {v: k for k, v in classMap.iteritems()}
    return classMapReversed_[t]

