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

class FreeVariableGraph(object):
    """Within this class, a 'chain' is a free variable member acces chain, representing something like
    var.member1.member2. ..., held as a tuple of strings of names

    and all of these expressionId's, I believe, are from function expressions
    """
    def __init__(self, rootExpressionId):
        self.rootExpressionId = rootExpressionId
        self.expressionIdToExpressionAndChain = {}
        self.convertedExpressions = {}
        self.expressionIdToDependentExpressionIdToChain = {}

    def expressionIds(self):
        return set(self.expressionIdToDependentExpressionIdToChain.keys())

    def expressionIdToDependentExpressionIds(self, expressionId):
        return self.expressionIdToDependentExpressionIdToChain[expressionId].keys()

    def expressionIdGraph(self):
        return {
            expressionId: self.expressionIdToDependentExpressionIdToChain[expressionId].keys() \
            for expressionId in self.expressionIdToDependentExpressionIdToChain.keys()
            }

    def expressionForExpressionId(self, expressionId):
        (expression, _) = self.expressionIdToExpressionAndChain[expressionId]
        return expression

    # this is not a clear concept. we're using it just as the name of any given function,
    # and assuming it's only length 1
    def chainForExpressionId(self, expressionId):
        (_, chain) = self.expressionIdToExpressionAndChain[expressionId]
        return chain

    def expressionAndChainForExpressionId(self, expressionId):
        return self.expressionIdToExpressionAndChain[expressionId]


