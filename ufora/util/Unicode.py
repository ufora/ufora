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

def convertToStringRecursively(inobject):
    '''
    custom object decoder to get rid of unicode from objects loaded with json.loads
    '''
    if isinstance(inobject, dict):
        return {convertToStringRecursively(key) : convertToStringRecursively(value)
                for key, value in inobject.iteritems()}
    elif isinstance(inobject, list):
        return [convertToStringRecursively(x) for x in inobject]
    elif isinstance(inobject, unicode):
        return str(inobject)
    else:
        return inobject

