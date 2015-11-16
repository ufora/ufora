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

import collections as collections

def new_type_description(typename, field_names):
    T = collections.namedtuple(typename, field_names + " typeName")
    T.__new__.__defaults__ = (None,) * len(T._fields)
    prototype = T(typeName=typename)
    T.__new__.__defaults__ = tuple(prototype)
    return T

def fromDict(value_dict):
    return globals()[value_dict["typeName"]](**value_dict)

def fromList(values):
    typeName = values[-1]
    return globals()[typeName](*values)

def deserialize(value_dict):
    if isinstance(value_dict, collections.Mapping):
        return fromDict(value_dict)
    else:
        return fromList(value_dict)

Primitive = new_type_description(
    'Primitive',
    'value'
    )
Tuple = new_type_description(
    'Tuple',
    'memberIds'
    )
Dict = new_type_description(
    'Dict',
    'keyIds, valueIds'
    )
List = new_type_description(
    'List',
    'memberIds'
    )
File = new_type_description(
    'File',
    'path, text'
    )
FunctionDefinition = new_type_description(
    'FunctionDefinition',
    'sourceFileId, lineNumber, freeVariableMemberAccessChainsToId'
    )
ClassDefinition = new_type_description(
    'ClassDefinition',
    'sourceFileId, lineNumber, freeVariableMemberAccessChainsToId'
    )
ClassInstanceDescription = new_type_description(
    'ClassInstanceDescription',
    'classId, classMemberNameToClassMemberId'
    )
WithBlockDescription = new_type_description(
    'WithBlockDescription',
    'freeVariableMemberAccessChainsToId, sourceFileId, lineNumber'
    )
RemotePythonObject = new_type_description(
    'RemotePythonObject',
    'computedValueArgument'
    )
NamedSingleton = new_type_description(
    'NamedSingleton',
    'singletonName'
    )
BuiltinExceptionInstance = new_type_description(
    'BuiltinExceptionInstance',
    'builtinExceptionTypeName, argsId'
    )
InstanceMethod = new_type_description(
    'InstanceMethod',
    'instanceId, methodName'
    )
