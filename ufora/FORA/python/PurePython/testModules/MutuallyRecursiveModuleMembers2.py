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

aGlobal = 42

def f1(x):
    if x <= 0:
        return x

    return f2(x)

def f2(x):
    return aGlobal + f4(x) + f3(x)

def f3(x):
    return f1(x - 1)

def f4(x):
    if x <= 0:
        return x

    return f5(x)

def f5(x):
    return aGlobal + f6(x) + f4(x - 1)

anotherGlobal = 1337

def f6(x):
    return anotherGlobal + x

