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
    type: 'type',
    object: 'object',
    Exception: 'Exception',
    UserWarning: 'UserWarning',
    TypeError: 'TypeError',
    ValueError: 'ValueError',
    AttributeError: 'AttributeError',
    ZeroDivisionError: 'ZeroDivisionError',
    ValueError: 'ValueError',
    IndexError: 'IndexError'
    }

singletonNameToObject = {
    'type': type,
    'object': object,
    'Exception': Exception,
    'UserWarning': UserWarning,
    'TypeError': TypeError,
    'ValueError': ValueError,
    'AttributeError': AttributeError,
    'ZeroDivisionError': ZeroDivisionError,
    'IndexError': IndexError
    }

pythonNameToPyforaName = {
    'type': 'Type',
    'object': 'Object',
    'Exception': 'Exception',
    'TypeError': 'TypeError',
    'ValueError': 'ValueError',
    'UserWarning': 'UserWarning',
    'AttributeError': 'AttributeError',
    'ZeroDivisionError': 'ZeroDivisionError',
    'ValueError': 'ValueError',
    'IndexError': 'IndexError'
    }

