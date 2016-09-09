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

class EvaluatorBase(object):
    '''The interface which all Evaluators must expose. Not intended
    to be instantiated'''
    def getVDM(self):
        raise NotImplementedError()

    def evaluate(self, *args):
        raise NotImplementedError()

    def flush(self):
        raise NotImplementedError()

    @staticmethod
    def expandIfListOrTuple(*args):
        """Checks if args is a collection of only one item and that item is a list or a tuple.
            If that's the case it returns the list or tuple. Otherwise it returns args.
        """
        if len(args) == 1 and isinstance(args[0], tuple) or isinstance(args[0], list):
            return args[0]
        else:
            return args



