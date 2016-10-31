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

import ufora.FORA.python.ParseException as ParseException
import ufora.FORA.python.ForaValue as ForaValue
import ufora.native.FORA as ForaNative

def freshVarname(startingName, namesUsed):
    """pick a variant on 'startingName' that's not in namesUsed"""
    if startingName not in namesUsed:
        return startingName
    ix = 1
    while True:
        name = startingName + "_" + str(ix)
        if name not in namesUsed:
            return name
        ix = ix + 1


class NameExistsButDoesntParseException(object):
    def __init__(self, projectNode, name):
        self.projectNode = projectNode
        self.name = name

    @property
    def childrenWhoDontParse(self):
        return self.projectNode.childrenWhoDontParse


class Expression(object):
    """Represents a FORA expression."""
    def __init__(self, nativeExpression, codeDefinitionPoint):
        assert isinstance(nativeExpression, ForaNative.Expression)
        self.nativeExpression_ = nativeExpression
        self.codeDefinitionPoint_ = codeDefinitionPoint

    #returns a list of variables that are 'free' in the expression
    freeVariables = property(lambda self: self.nativeExpression_.freeVariables)

    #returns a list of variables that are mentioned anywhere in the expression
    mentionedVariables = property(lambda self: self.nativeExpression_.mentionedVariables)

    #returns a list of free variables that are assigned to by the expression
    assignedVariables = property(lambda self: self.nativeExpression_.assignedVariables)

    #returns a list of pairs of strings representing expressions like "x.y"
    #where "x" is a free variable and "y" is a member. used to rebind things in
    #the expression
    freeVariableMemberAccesses = property(lambda self:
                                        self.nativeExpression_.freeVariableMemberAccesses)

    def packAssignedVarsIntoTuple(self):
        """Return an expression that returns the value of the expression and also any assigned variables.

        If 'self' is 'e', this expression returns (e, (a1, a2, ...)) where the a's are assigned
        variables in the environment sorted alphabetically.

        If the expression throws an exception/stacktrace pair, the new expression throws

            (exception, (a1, a2, ...))

        from the same stacktrace.

        This function may not be called on an expression with return statements in it.
        """
        return Expression(self.nativeExpression_.packAssignedVarsIntoTuple(), self.codeDefinitionPoint_)

    def freeVariableUsePoints(self, varname):
        """return a list of CodeLocations where 'varname' is free"""
        return self.nativeExpression_.getFreeVariableRanges(varname)

    def getReturnStatementPoints(self):
        """return a list of CodeLocations where the expression has a 'return' statement"""
        return self.nativeExpression_.getReturnStatementRanges()

    def assignedVariableUsePoints(self, varname):
        """return a list of CodeLocations where a free variable 'varname' is assigned to"""
        return self.nativeExpression_.getAssignedVariableRanges(varname)

    def toFunction(self):
        """convert to a function with one argument per free variable"""
        return ForaValue.FORAValue(self.nativeExpression_.toFunctionImplval(False))

    def toFunctionAsImplval(self):
        """convert to a function with one argument per free variable"""
        return self.nativeExpression_.toFunctionImplval(False)

    def toFunctionAsImplvalWithPassthroughArgument(self):
        """convert to a function with one argument per free variable, plus an extra argument
            that gets added to the final result as a tuple."""
        return self.nativeExpression_.toFunctionImplvalWithPassthroughArgument(False)

    def rebindFreeVariableMemberAccess(self, varname, memberName, newName):
        """convert expressions like 'x.y' where 'x' is free to a new free
        variable"""
        return Expression(
            self.nativeExpression_.rebindFreeVariableMemberAccess(
                varname,
                memberName,
                newName
                ),
            self.codeDefinitionPoint_
            )

    def raiseParseException_(self, functionParseError):
        raise ParseException.ParseException(
            functionParseError,
            self.codeDefinitionPoint_
            )

    def raiseIfUsesUndefinedVariables(self, knownVariables):
        for variable in self.assignedVariables:
            self.checkVariableInKnownVariables(variable, knownVariables)

    def checkVariableInKnownVariables(self, variable, knownVariables):
        if variable not in knownVariables:
            assignmentLocations = self.assignedVariableUsePoints(variable)
            assert assignmentLocations, "Can't find assignment point for %s in '%s'." % (variable, str(self))

            self.raiseParseException_(
                ForaNative.FunctionParseError(
                    "can't assign to free variable " + variable,
                    assignmentLocations[0].range
                    )
                )

    def raiseParseErrorIfHasReturnStatements(self):
        getReturnStatementPoints = self.getReturnStatementPoints()
        if getReturnStatementPoints:
            self.raiseParseException_(
                ForaNative.FunctionParseError(
                    "can't use a return statement in a command-line expression",
                    getReturnStatementPoints[0].range
                    )
                )

    def specializeFreeVariableMapping(self,
                freeVariableMapping,
                specializationFunc,
                lookupFunc,
                finalVariableValueValidator
                ):
        """Allow an expression containing expressions like 'm.x' to be specialized.

        If we know what 'm' binds to, and

            specializationFunc(freeVariableMapping[m], 'x')

        produces a non-null value, we rebind the free variable to a new name with the result
        of specialzationFunc.

        Finally, we call 'finalVariableValueValidator' with the value each variable chain
        has been resolved to, along with a string of dot-separated identifiers. This function
        should return an error string if the intermediate value that has been bound is invalid.
        """
        done = False
        checkedNames = set()
        expr = self

        dotSequences = {}

        # Search through all the free variables and look up their values using the given lookup
        # function.
        for varname in self.freeVariables:
            dotSequences[varname] = varname
            if varname not in freeVariableMapping:
                varValue = lookupFunc(varname)

                if varValue is None:
                    codeLocations = self.freeVariableUsePoints(varname)

                    raise ParseException.ParseException(
                        ForaNative.FunctionParseError(
                            "Couldn't resolve free variable '%s'" % (varname,),
                            codeLocations[0].range
                            ),
                        self.codeDefinitionPoint_
                        )

                elif isinstance(varValue, NameExistsButDoesntParseException):
                    raise ParseException.ParseException(
                        ForaNative.FunctionParseError(
                            "Some modules did not parse correctly.",
                            self.freeVariableUsePoints(varname)[0].range
                            ),
                        self.codeDefinitionPoint_
                        )

                freeVariableMapping[varname] = varValue



        while not done:
            done = True
            #freeVariables = expr.freeVariables
            freeVariablesBound = expr.freeVariableMemberAccesses

            for varname, memberName in freeVariablesBound:
                if varname not in freeVariableMapping:
                    freeVariableMapping[varname] = lookupFunc(varname)
                mapsTo = freeVariableMapping[varname]
                if (mapsTo is not None and varname not in checkedNames):
                    subNode = specializationFunc(mapsTo, memberName)
                    if subNode is not None:
                        #we can bind this value to the node
                        newName = freshVarname(varname + "_" + memberName, set(expr.mentionedVariables))

                        dotSequences[newName] = dotSequences[varname] + "." + memberName

                        expr = expr.rebindFreeVariableMemberAccess(varname, memberName, newName)
                        freeVariableMapping[newName] = subNode
                        done = False
                    else:
                        checkedNames.add(varname)

        for var in expr.freeVariables:
            errString = finalVariableValueValidator(freeVariableMapping[var], dotSequences[var])

            if errString is not None:
                raise ParseException.ParseException(
                    ForaNative.FunctionParseError(
                        errString,
                        expr.freeVariableUsePoints(var)[0].range
                        ),
                    self.codeDefinitionPoint_
                    )

        return expr

    def returnFreeVariableValues(self, locals, importFunction):
        """Return arguments for the free variables in expression.

        importFunction = a function to call with free symbols that aren't in
            locals to look them up
        """
        boundVariables = []

        for freeVariable in self.freeVariables:
            if freeVariable in locals:
                boundVariables += [locals[freeVariable]]
            else:
                binding = importFunction(freeVariable)

                if binding is None:
                    raise ParseException.ParseException(
                        ForaNative.FunctionParseError(
                            "Couldn't resolve free variable '%s'" % freeVariable,
                            self.freeVariableUsePoints(freeVariable)[0].range
                            ),
                        self.codeDefinitionPoint_
                        )
                else:
                    boundVariables += [binding]

        return boundVariables


    @staticmethod
    def parse(textToParse, codeDefinitionPoint = None, nameScope = "<eval>", parseAsModule=False):
        """parse a string to an Expression object or throw a FunctionParseError.

        textToParse - a string containing the FORA expression
        parsePath - a list of strings containing the path to the
            code being parsed. this will show up in any stacktraces
            thrown by this expression or by code called by this expression
        nameScope - the name that functions and objects should descend from. If the
            expression is a simple 'fun' or 'object', this will be its name
        """

        if codeDefinitionPoint is None:
            codeDefinitionPoint = \
                ForaNative.CodeDefinitionPoint.ExternalFromStringList(
                    [nameScope]
                    )

        if parseAsModule:
            nativeExpressionOrParseError = \
                ForaNative.parseObjectDefinitionBodyToExpression(
                    textToParse,
                    ["Tsunami", nameScope + ".fora"],
                    False,
                    nameScope,
                    nameScope
                    )
        else:
            nativeExpressionOrParseError = \
                ForaNative.parseStringToExpression(
                    textToParse,
                    codeDefinitionPoint,
                    nameScope
                    )

        if isinstance(nativeExpressionOrParseError, ForaNative.FunctionParseError):
            raise ParseException.ParseException(
                nativeExpressionOrParseError,
                codeDefinitionPoint
                )

        return Expression(nativeExpressionOrParseError, codeDefinitionPoint)

    def __str__(self):
        return str(self.nativeExpression_)

