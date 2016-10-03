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
import types
import ufora.BackendGateway.Observable as Observable

# DO NOT REMOVE: this allows users of this module to use
# the 'observable' decorator without having to know about the 'Observable'
# module.
from ufora.BackendGateway.Observable import observable


CumulusEnvironment = collections.namedtuple(
    'CumulusEnvironment',
    'cumulus_gateway cache_loader computations object_converter'
    )


class SubscribableObject(Observable.Observable):
    def __init__(self, id, cumulus_env):
        super(SubscribableObject, self).__init__()
        self.id = id
        self.cumulus_gateway = cumulus_env.cumulus_gateway
        self.cache_loader = cumulus_env.cache_loader
        self.computations = cumulus_env.computations
        self.object_converter = cumulus_env.object_converter



def ExposedFunction(expandArgs=False):
    """Create a function to expose over the socket.io protocol.

    expandArgs = pass the single socket.io args argument as a list or kwds argument.
    """
    if isinstance(expandArgs, bool):
        def decorator(f):
            f.func_dict['exposed'] = True
            f.func_dict['expand_args'] = expandArgs
            return f
        return decorator

    f = expandArgs
    expandArgs = False
    f.func_dict['exposed'] = True
    f.func_dict['expand_args'] = expandArgs
    return f


def ExposedProperty(f):
    f.func_dict['exposed'] = True
    return property(f)


def isFunctionToExpose(classMember):
    return (
        (isinstance(classMember, types.FunctionType) or isinstance(classMember, types.MethodType))
        and classMember.func_dict.get('exposed', False)
        )


def functionExpectsExpandedArgs(classMember):
    return (isFunctionToExpose(classMember)
            and classMember.func_dict.get('expand_args', False))


def isPropertyToExpose(classMember):
    return isinstance(classMember, property) and classMember.fget.func_dict.get('exposed', False)
