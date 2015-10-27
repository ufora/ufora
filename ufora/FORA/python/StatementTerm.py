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

import ufora.native.FORA as ForaNative
import ufora.FORA.python.ParseException as ParseException
import ufora.FORA.python.Expression as Expression
import logging

class StatementTerm(object):
    def __init__(self, nativeStatementTerm, codeDefPoint):
        self.nativeStatementTerm_ = nativeStatementTerm
        self.codeDefPoint_ = codeDefPoint

    def getNativeTerm(self):
        return self.nativeStatementTerm_
        
    def unpackToExpression(self):
        """Returns the StatementTerm as an Expression.

        The resulting expression returns

            ((l1, l2, ...), e)

        where 'e' is the result of the whole expression, the l's are the
        variables in the given let assignment (if any) and the a's are
        variables in the calling context that are assigned to.

        This function verifies that every 'assigned' variable is
        available in the calling context.
        """
        symbolsBoundInLetStatement, nativeExpression = self.nativeStatementTerm_.extractExpressionAndBoundVariables()

        expression = Expression.Expression(nativeExpression, self.codeDefPoint_)

        return symbolsBoundInLetStatement, expression

    def extractCodeLocation(self):
        """Return the codelocation for this statement term. 

        If this is an expression, returns a CodeLocation. If it's a let binding, it returns a 
        list of pairs containing the stringified let binding and to the code location.
        """
        return self.nativeStatementTerm_.extractCodeLocation()

    def extractCodeLocationId(self):
        return self.nativeStatementTerm_.extractCodeLocationId()

    def __str__(self):
        return str(self.nativeStatementTerm_)

    def hash(self):
        return self.nativeStatementTerm_.hash()
        
    @staticmethod
    def parseToStatementTermList(textToParse, codeDefinitionPoint, nameScope):
        """parse a string to a list of StatementTerms, or throw an exception.

        textToParse - a string containing the FORA expression
        stacktraceIdentity - a list of strings containing the path to the
            code being parsed. this will show up in any stacktraces
            thrown by this expression or by code called by this expression
        """
        statementTermListOrError = \
            ForaNative.parseStringToStatementTermsWithLocationInfo(
                textToParse,
                codeDefinitionPoint,
                nameScope
                )

        if isinstance(statementTermListOrError, ForaNative.FunctionParseError):
            raise ParseException.ParseException(statementTermListOrError, codeDefinitionPoint)

        return [StatementTerm(x, codeDefinitionPoint) for x in  statementTermListOrError]


