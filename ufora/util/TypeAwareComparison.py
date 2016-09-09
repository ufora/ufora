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


def typecmp(self, other, ownTypeComp):
    '''
    Compares objects of varying types. If they are different types it returns the lexical
    comparison of their type string. Otherwise it uses the provided type comparison callable
    '''
    if self.__class__ != other.__class__:
        return cmp(self.__class__, other.__class__)
    return ownTypeComp(self, other)

