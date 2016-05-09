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

class OperationsToTest(object):

    @staticmethod
    def allOperations():

        def add(x, y):
            return x + y

        def mult(x, y):
            return x * y

        def div(x, y):
            return x / y

        def sub(x, y):
            return x - y

        def eq(x, y):
            return x == y

        def ne(x, y):
            return x != y

        def gt(x, y):
            return x > y

        def lt(x, y):
            return x < y

        def power(x, y):
            return x ** y

        def xor(x, y):
            return x ^ y

        return [add, mult, div, sub, eq, ne, gt, lt, power, xor]

