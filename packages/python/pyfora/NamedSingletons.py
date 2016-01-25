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

"""NamedSingletons

A manifest of python objects that have explicit FORA implementations in the purePython module.
"""

pythonSingletonToName = {
    AssertionError: 'AssertionError',
    bool: 'bool',
    dict: 'dict',
    float: 'float',
    int: 'int',
    isinstance: 'isinstance',
    issubclass: 'issubclass',
    list: 'list',
    object: 'object',
    slice: 'slice',
    str: 'str',
    tuple: 'tuple',
    type: 'type',
    type(None): 'NoneType',
    AttributeError: 'AttributeError',
    Exception: 'Exception',
    IndexError: 'IndexError',
    TypeError: 'TypeError',
    NotImplementedError: 'NotImplementedError',
    UserWarning: 'UserWarning',
    UnboundLocalError: 'UnboundLocalError',
    ValueError: 'ValueError',
    ZeroDivisionError: 'ZeroDivisionError'
    }

singletonNameToObject = {v:k for k,v in pythonSingletonToName.iteritems()}

pythonNameToPyforaName = {
    'AssertionError': 'AssertionError',
    'bool': 'BoolType',
    'dict': 'DictType',
    'float': 'FloatType',
    'int': 'IntType',
    'isinstance': 'IsInstance',
    'issubclass': 'IsSubclass',
    'list': 'ListType',
    'object': 'Object',
    'slice': 'SliceType',
    'str': 'StrType',
    'tuple': 'TupleType',
    'type': 'Type',
    'AttributeError': 'AttributeError',
    'Exception': 'Exception',
    'IndexError': 'IndexError',
    'NoneType': 'NoneType',
    'NotImplementedError': 'NotImplementedError',
    'TypeError': 'TypeError',
    'UserWarning': 'UserWarning',
    'UnboundLocalError': 'UnboundLocalError',
    'ValueError': 'ValueError',
    'ZeroDivisionError': 'ZeroDivisionError'
    }

