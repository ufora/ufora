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

import dis
import opcode

LOAD_FAST = opcode.opmap['LOAD_FAST']
LOAD_ATTR = opcode.opmap['LOAD_ATTR']
RETURN_VALUE = opcode.opmap['RETURN_VALUE']

def isSimpleFunction(x):
    """if a function looks like lambda self: self.a.b.c...,
    this function returns (True, ['a',b,'...]) otherfwise (False, ())
    """
    if not isinstance(x, type(lambda:0)):
        return False, ()
    c = x.func_code.co_code
    vals = [ord(op) for op in c]
    if x.func_code.co_argcount != 1:
        return False, ()

    if not vals:
        return False, ()

    if vals[0] != LOAD_FAST:
        return False, ()
    if vals[1] != 0 or vals[2] != 0:
        return False, ()
    if vals[-1] != RETURN_VALUE:
        return False, ()

    if (len(vals) - 1) % 3 != 0:
        return False, ()

    loads = (len(vals) - 1)/3
    if vals[3:-1:3] != [LOAD_ATTR] * (loads-1):
        return False, ()
    if vals[2::3] != [0] * loads:
        return False, ()

    lookups = []
    varnames = x.func_code.co_names
    lookups = [varnames[l] for l in vals[4::3]]
    return True, lookups

