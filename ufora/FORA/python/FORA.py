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

"""a python wrapper around FORA Values that allow users to work with the


This is the primary interface for clients who want to work with FORA in
python programs but who don't need control over internal FORA details.

Note: initializing this module activates the FORA import hooks in python.
"""
import ufora.config.Setup as Setup

import ufora.native.Cumulus as CumulusNative
import ufora.native.FORA as ForaNative
import ufora.native.Hash as HashNative

import ufora.FORA.python.ParseException as ParseException
import ufora.FORA.python.StatementTerm as StatementTerm
import ufora.FORA.python.Runtime as Runtime
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.FORA.python.Evaluator.Evaluator as Evaluator
import ufora.FORA.python.ForaValue as ForaValue
import ufora.FORA.python.ModuleImporter as ModuleImporter
import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager

import logging
import traceback

Function = ForaNative.Function

Nothing = ForaValue.FORAValue(ForaNative.Nothing)
nothing = ForaValue.FORAValue(ForaNative.nothing)
true = ForaValue.FORAValue(ForaNative.true)
false = ForaValue.FORAValue(ForaNative.false)
Int64 = ForaValue.FORAValue(ForaNative.Int64)
UInt64 = ForaValue.FORAValue(ForaNative.UInt64)
Int32 = ForaValue.FORAValue(ForaNative.Int32)
UInt32 = ForaValue.FORAValue(ForaNative.UInt32)
Int16 = ForaValue.FORAValue(ForaNative.Int16)
UInt16 = ForaValue.FORAValue(ForaNative.UInt16)
Int8 = ForaValue.FORAValue(ForaNative.Int8)
UInt8 = ForaValue.FORAValue(ForaNative.UInt8)
UInt1 = ForaValue.FORAValue(ForaNative.UInt1)
Bool = UInt1
Float32 = ForaValue.FORAValue(ForaNative.Float32)
Float64 = ForaValue.FORAValue(ForaNative.Float64)
Symbol = ForaValue.FORAValue(ForaNative.Symbol)
String = ForaValue.FORAValue(ForaNative.String)
Identical = ForaValue.FORAValue(ForaNative.makeSymbol("Identical"))

def tupleNames(foraTuple):
    if isinstance(foraTuple, tuple):
        return [None] * len(foraTuple)
    elif isinstance(foraTuple, ForaValue.FORATuple):
        return foraTuple.names_
    else:
        raise Exception("Expected a tuple")

def makeSymbol(symbolname):
    return ForaValue.FORAValue(ForaNative.makeSymbol(symbolname))

def makeTag(tagname):
    return ForaValue.FORAValue(ForaNative.makeTag(tagname))

def isValueOrException(x):
    """return True if x is a ForaValue.FORAValue or a FORAException"""
    return isinstance(x, (ForaValue.FORAValue, ForaValue.FORAException))

def pythonToFORA(x):
    """take a python object 'x' and create the biggest FORA value possible.

    copies as much data into FORA as it can.
    """
    return ForaValue.FORAValue(ForaNative.pythonToFORA(x))

def isVector(foraValue):
    return isinstance(foraValue, ForaValue.FORAVector)

def isTuple(foraValue):
    return isinstance(foraValue, (tuple, ForaValue.FORATuple))

def isCST(foraValue):
    """returns whether a foraValue is a constant"""
    return foraValue.implVal_.isCST

def extractImplValContainer(foraValue):
    """the preferred way to get the implval out of a ForaValue.FORAValue object"""
    return foraValue.implVal_

def objectMetadata(val):
    """given a value 'val', return a ForaValue.FORAValue with the object's metadata"""
    return ForaValue.FORAValue.symbol_ExtractMetadata(val)

def objectMembers(val):
    """given a value 'val', return a dict containing the named members and
    their metadatas"""
    res = objectMetadata(val)

    try:
        metas = res.members

        members = val.implVal_.objectMembers
        assert len(metas) == len(members), (len(metas), len(members))
        tr = {}
        for ix in range(len(members)):
            tr[members[ix]] = metas[ix]
        return tr
    except:
        return {}


class ExpressionEvaluator(object):
    def evaluateCodeBlock(
            self,
            text,
            evalPrefixes='',
            bindings=None,
            lookupFunc=ModuleImporter.importModuleByName
            ):
        assert isinstance(text, str), text

        if isinstance(evalPrefixes, str):
            evalPrefixes = tuple(evalPrefixes)

        if bindings is None:
            bindings = {}

        assert isinstance(bindings, dict), bindings

        lines = text.split('\n')

        while len(lines) > 0:
            orig_line = lines.pop(0)
            line = orig_line.lstrip()

            if not line.startswith(evalPrefixes) and not line.startswith("| "):
                yield (orig_line, line, None)
                continue

            wrapBlockInParens = False
            results = None
            while len(lines) > 0 and not lines[0].startswith(evalPrefixes):
                newline = lines.pop(0)
                if newline.startswith("| "):
                    wrapBlockInParens = True
                    newline = newline[2:]
                line += '\n' + newline

            tmpLine = line.rstrip()
            for prefix in evalPrefixes:
                if tmpLine.startswith(prefix):
                    # Extra parens ensures that MutableVectors work properly. Hopefully, this will
                    # be fixed in the evaluator itself soon. - william, 2013-06-12
                    if wrapBlockInParens:
                        tmpLine = "(" + tmpLine[len(prefix):].lstrip() + ")"
                    else:
                        tmpLine = tmpLine[len(prefix):].lstrip()
                    results = {}
                    for result in self.evaluateExpression(tmpLine, bindings, lookupFunc=lookupFunc):
                        for name, value in result.iteritems():
                            results[name] = value
                    break

            if wrapBlockInParens:
                yield (orig_line, tmpLine[1:-1], results)
            else:
                yield (orig_line, tmpLine, results)


    def evaluateExpression(
                self,
                expr,
                bindings=None,
                parsePath=None,
                nameScope="<eval>",
                lookupFunc=ModuleImporter.importModuleByName,
                specializerFunc=lambda value, membername: None,
                variableBindingValidator=lambda value, membersequence: None
                ):
        assert isinstance(expr, str), expr

        if bindings is None:
            bindings = {}

        assert isinstance(bindings, dict), bindings

        if isinstance(parsePath, ForaNative.CodeDefinitionPoint):
            codeDefinitionPoint = parsePath
        else:
            if parsePath is None:
                parsePath = [nameScope]

            assert isinstance(parsePath, list), \
                "parsePath argument must be a list of strings, not %s" % parsePath

            for p in parsePath:
                assert isinstance(p, str), "parsePath argument must be a list of strings, not %s " % p

            codeDefinitionPoint = \
                ForaNative.CodeDefinitionPoint.ExternalFromStringList(
                    parsePath
                    )

        statementTerms = []
        # Check for parse errors at the StatementTerm level. This maintains the behavior needed for
        # the evaluateCodeBlock method, which evaluates code in docstrings and the KB. We actually
        # want parse errors to be returned as values, so we can print those errors, not halt
        # execution. 2014-01-15 william.
        try:
            statementTerms = StatementTerm.StatementTerm.parseToStatementTermList(
                expr,
                codeDefinitionPoint,
                nameScope
                )
        except ParseException.ParseException as e:
            # Don't include the JSON description here in the 'result' field, since the
            # LocalEvaluator actually checks for the ParseException instance.
            # 2014-01-25 william
            yield {'isParseError' : True, 'result' : e}

        for statementTerm in statementTerms:
            try:
                symbolsBoundInRootLetStatements, expressionWithAssignments = \
                    statementTerm.unpackToExpression()

                #verify that it's legal to turn embed the expression's assignments
                #in its return values
                expressionWithAssignments.raiseIfUsesUndefinedVariables(bindings)
                expressionWithAssignments.raiseParseErrorIfHasReturnStatements()

                expression = expressionWithAssignments.packAssignedVarsIntoTuple()

                assignments = expressionWithAssignments.assignedVariables

                expression = expression.specializeFreeVariableMapping(
                    bindings,
                    specializerFunc,
                    lookupFunc,
                    variableBindingValidator
                    )

                argsForFreeVariables = expression.returnFreeVariableValues(bindings, lookupFunc)

                yield self.evaluate(
                    expression,
                    argsForFreeVariables,
                    assignments,
                    symbolsBoundInRootLetStatements,
                    bindings,
                    statementTerm
                    )

            except ParseException.ParseException as e:
                # Don't include the JSON description here in the 'result' field, since the
                # LocalEvaluator actually checks for the ParseException instance.
                yield {'isParseError' : True, 'result' : e}

class LocalExpressionEvaluator(ExpressionEvaluator):
    def evaluate(self, expr, args, assignments, lets, binding, statementTerm):
        exprAsFunction = expr.toFunction()

        args = [exprAsFunction.implVal_, ForaValue.FORAValue.symbol_Call.implVal_] + args

        res = Evaluator.evaluator().evaluate(*args)
        # res is a ComputationResult instance, defined in ufora/FORA/Core/ComputationResult.hppml
        #@type ComputationResult =
        #       Exception of ImplValContainer exception
        #    -| Result of ImplValContainer result
        #    -| Failure of ErrorState error

        resVal = None
        if res.isResult():
            resVal = res.asResult.result
        elif res.isException():
            resVal = res.asException.exception
        elif res.isFailure():
            raise ForaValue.FORAFailure(res.asFailure.error)

        # At this point, resVal is an ImplValContainer
        resVal = ForaValue.FORAValue(resVal).implVal_

        boundValues = {}

        if res.isException():
            #the exception it a tuple ((exception, (a1, a2, ...)), stacktrace)
            #we want to propagate (exception, stacktrace)
            exceptionAndVariables, stacktrace = resVal
            exception, variableAssignments = exceptionAndVariables

            #iterate through the binding and update the original
            for ix, a in enumerate(assignments):
                boundValues[a] = binding[a] = variableAssignments[ix]

            boundValues['result'] = ForaValue.FORAException((exception, ForaValue.FORAValue(stacktrace)))
        else:
            #packAssignedVarsIntoTuple puts the result in the first tuple element
            #and the assigned variables in the second
            actualResult, boundSymbolValues, assignedOutputs = resVal

            #iterate through the binding and update the original
            for ix, a in enumerate(lets):
                boundValues[a] = binding[a] = boundSymbolValues[ix]

            for ix, a in enumerate(assignments):
                boundValues[a] = binding[a] = assignedOutputs[ix]

            boundValues['result'] = actualResult

        return boundValues

LOCAL_EVAL = LocalExpressionEvaluator()

def eval(   toEvaluate,
            locals = None,
            parsePath = None,
            keepAsForaValue = False,
            nameScope = "<eval>"
            ):
    """evaluate some FORA code and return the result.

    toEvaluate - a string containing FORA code to evaluate
    locals - a dictionary of variables that may be free in the expression. If
        they are assigned to, 'locals' is updated.
    parsePath - context information about the location from which the evaluation
        is requested
    nameScope - the name scope to use for functions and objects. if the expression is a simple
        'fun' or 'object' expression, this is the name it will have

    returns a ForaValue.FORAValue or raises a ForaValue.FORAException
    """
    binding = {}
    if locals:
        for key in locals:
            value = locals[key]
            if isinstance(value, ForaNative.ImplValContainer):
                binding[key] = value
            if isinstance(value, ForaValue.FORAValue):
                binding[key] = value.implVal_
            else:
                binding[key] = ForaValue.FORAValue(value).implVal_

    try:
        changes = LOCAL_EVAL.evaluateExpression(toEvaluate, binding, parsePath, nameScope)
        mergedChanges = {}
        result = None
        for c in changes:
            for name, value in c.iteritems():
                mergedChanges[name] = value

            result = mergedChanges['result']

            if isinstance(result, ParseException.ParseException):
                raise result

            if isinstance(result, ForaValue.FORAException):
                result.foraVal = ForaValue.FORAValue(result.foraVal)
                if not keepAsForaValue:
                    result.foraVal = result.foraVal.toPythonObject()
                raise result

        result = ForaValue.FORAValue(result)
        if not keepAsForaValue:
            result = result.toPythonObject()
        return result
    finally:
        if locals is not None:
            for key in binding:
                locals[key] = ForaValue.FORAValue(binding[key])
                if not keepAsForaValue:
                    locals[key] = locals[key].toPythonObject()


def importModule(modulePath):
    #TODO BUG anybody:  why is this here? It was getting passed as the
    #searchForFreeVariables argument to importModuleFromPath for some reason
    ModuleImporter.builtinModuleImplVal()
    return ForaValue.FORAValue(
                ModuleImporter.importModuleFromPath(
                    modulePath,
                    True
                    )
                )

#the 'builtin' module
_builtin = None

def reloadBuiltin():
    global _builtin
    ModuleImporter.initialize(reimport = True)
    _builtin = ForaValue.FORAValue(ModuleImporter.builtinModuleImplVal())

def isInitialized():
    return _builtin is not None

def initialize(setupObjectToUse = None, useLocalEvaluator = True):
    global _builtin
    if _builtin is not None:
        return

    Runtime.initialize(setupObjectToUse)
    ModuleImporter.initialize(setupObjectToUse)
    Evaluator.initialize(setupObjectToUse, useLocalEvaluator)

    _builtin = ForaValue.FORAValue(ModuleImporter.builtinModuleImplVal())


def builtin():
    global _builtin
    if _builtin is None:
        raise Setup.InitializationException("FORA.py is not initialized!")
    return _builtin

