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


import collections



NoneType = type(None)

def isPrimitive(pyObject):
    return isinstance(pyObject, (NoneType, int, float, str, bool))


def type_description(typename, field_names):
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


def serialize(object_definition):
    if isPrimitive(object_definition) or isinstance(object_definition, list):
        return object_definition
    return object_definition._asdict()


def deserialize(value):
    if isPrimitive(value) or isinstance(value, list):
        return value
    if isinstance(value, collections.Mapping):
        return fromDict(value)
    return fromList(value)


Tuple = type_description(
    'Tuple',
    'memberIds'
    )
Dict = type_description(
    'Dict',
    'keyIds, valueIds'
    )
List = type_description(
    'List',
    'memberIds'
    )
File = type_description(
    'File',
    'path, text'
    )
FunctionDefinition = type_description(
    'FunctionDefinition',
    'sourceFileId, lineNumber, freeVariableMemberAccessChainsToId'
    )

# ClassDefinition:
#  sourceFileId: id of the File instance in which this class is defined
#  lineNumber: the line number in which the class definition appears
#  freeVariableMemberAccessChainToId: a dict freeVariableMemberAccessChain -> id
#  baseClassIds: a list of object ids of the immediate base classes of this class.
ClassDefinition = type_description(
    'ClassDefinition',
    'sourceFileId, lineNumber, freeVariableMemberAccessChainsToId, baseClassIds'
    )
ClassInstanceDescription = type_description(
    'ClassInstanceDescription',
    'classId, classMemberNameToClassMemberId'
    )
WithBlockDescription = type_description(
    'WithBlockDescription',
    'freeVariableMemberAccessChainsToId, sourceFileId, lineNumber'
    )
RemotePythonObject = type_description(
    'RemotePythonObject',
    'computedValueArgument'
    )
NamedSingleton = type_description(
    'NamedSingleton',
    'singletonName'
    )
BuiltinExceptionInstance = type_description(
    'BuiltinExceptionInstance',
    'builtinExceptionTypeName, argsId'
    )
InstanceMethod = type_description(
    'InstanceMethod',
    'instanceId, methodName'
    )
Unconvertible = type_description(
    'Unconvertible',
    ''
    )
