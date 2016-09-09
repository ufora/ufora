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

"""DefaultDict - dictionary with a default item

DefaultDict overrides a normal dict. When created, give it a lambda
function that takes a key and produces the 'zero' element for the dictionary
for that key.
"""

class DefaultDict(dict):
    def __init__(self, defaultFunction):
        dict.__init__(self)
        self.defaultFunction = defaultFunction
    def __getitem__(self, x):
        if not self.has_key(x):
            dict.__setitem__(self, x, self.defaultFunction(x))
        return dict.__getitem__(self,x)


