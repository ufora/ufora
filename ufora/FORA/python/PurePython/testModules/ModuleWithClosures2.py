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

aGlobal = 1

def f1(x, y):
    return f2(x)(y)

def f2(x):
    local = 2
    def tr(y):
        if y <= 1:
            return y
        return f3(x) + f4(y) + local + aGlobal

    return tr

def f3(x):
    return f4(x)

def f4(x):
    return f5(x) + f2(x - 1)(x - 1)

def f5(x):
    return aGlobal + x

