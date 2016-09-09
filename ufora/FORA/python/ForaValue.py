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
import ufora.FORA.python.Evaluator.Evaluator as Evaluator
import ufora.FORA.python.ErrorFormatting as ErrorFormatting

import ufora.util.TypeAwareComparison as TypeAwareComparison

import traceback

def evaluator():
    return Evaluator.evaluator()

class FORAFailure(Exception):
    """a wrapper around a FORA failure
    """
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return "ForaFailure(%s)" % self.error

class FORAValue(object):
    """a wrapper around a FORA value

    you may interact with this object as if it were a regular python object.
    methods will be offloaded to the FORA runtime itself.
    """
    def __init__(self, x = None):
        object.__init__(self)
        if x is None:
            self.implVal_ = ForaNative.nothing
        elif isinstance(x, FORAValue):
            self.implVal_ = x.implVal_
        elif isinstance(x, ForaNative.ImplValContainer):
            self.implVal_ = x
        elif isinstance(x, tuple):
            self.implVal_ = ForaNative.ImplValContainer(
                tuple([FORAValue(elt).implVal_ for elt in x])
                )
        else:
            #this will attempt to convert numerics
            #and will otherwise represent the value as a python object
            self.implVal_ = ForaNative.ImplValContainer(x)

    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            raise AttributeError() # we don't want to intercept special python methods

        return processComputationResult(
            Evaluator.evaluator().evaluate(
                self.implVal_,
                FORAValue.symbol_Member.implVal_,
                ForaNative.makeSymbol(attr)
                )
            )

    def __call__(self, *args):
        return processComputationResult(
            Evaluator.evaluator().evaluate(
                self.implVal_,
                FORAValue.symbol_Call.implVal_,
                *[FORAValue(x).implVal_ for x in args]
                )
            )

    def __getitem__(self, x):
        return processComputationResult(
            Evaluator.evaluator().evaluate(
                self.implVal_,
                FORAValue.symbol_GetItem.implVal_,
                FORAValue(x).implVal_
                )
            )

    def __setitem__(self, ix, x):
        return processComputationResult(
            Evaluator.evaluator().evaluate(
                self.implVal_,
                FORAValue.symbol_SetItem.implVal_,
                FORAValue(ix).implVal_,
                FORAValue(x).implVal_
                )
            )

    def __len__(self):
        return processComputationResult(
            Evaluator.evaluator().evaluate(
                FORAValue.symbol_Size.implVal_,
                FORAValue.symbol_Call.implVal_,
                self.implVal_
                )
            )

    def __add__(self, other):
        return binaryOp_(self, FORAValue(other), ForaOperatorSymbols.plus)

    def __radd__(self, other):
        return binaryOp_(FORAValue(other), self, ForaOperatorSymbols.plus)

    def __sub__(self, other):
        return binaryOp_(self, FORAValue(other), ForaOperatorSymbols.sub)

    def __rsub__(self, other):
        return binaryOp_(FORAValue(other), self, ForaOperatorSymbols.sub)

    def __mul__(self, other):
        return binaryOp_(self, FORAValue(other), ForaOperatorSymbols.mul)

    def __rmul__(self, other):
        return binaryOp_(FORAValue(other), self, ForaOperatorSymbols.mul)

    def __div__(self, other):
        return binaryOp_(self, FORAValue(other), ForaOperatorSymbols.div)

    def __rdiv__(self, other):
        return binaryOp_(FORAValue(other), self, ForaOperatorSymbols.div)

    def __mod__(self, other):
        return binaryOp_(self, FORAValue(other), ForaOperatorSymbols.mod)

    def __rmod__(self, other):
        return binaryOp_(FORAValue(other), self, ForaOperatorSymbols.mod)

    def __pow__(self, other):
        return binaryOp_(self, FORAValue(other), ForaOperatorSymbols.pow)

    def __rpow__(self, other):
        return binaryOp_(FORAValue(other), self, ForaOperatorSymbols.pow)

    def __lshift__(self, other):
        return binaryOp_(self, FORAValue(other), ForaOperatorSymbols.lshift)

    def __rlshift__(self, other):
        return binaryOp_(FORAValue(other), self, ForaOperatorSymbols.lshift)

    def __rshift__(self, other):
        return binaryOp_(self, FORAValue(other), ForaOperatorSymbols.rshift)

    def __rrshift__(self, other):
        return binaryOp_(FORAValue(other), self, ForaOperatorSymbols.rshift)

    def __cmp__(self, other):
        return TypeAwareComparison.typecmp(self, other,
            lambda self, other : cmp(self.implVal_, other.implVal_))

    def __hash__(self):
        return self.implVal_.__hash__()

    def __str__(self):
        x = self
        ix = 0
        while isinstance(x, FORAValue) and x.implVal_.type != String.implVal_:
            ix = ix + 1
            x = String(x)
            if (ix > 50):
                print x.implVal_.type, String, x.implVal_.type != String.implVal_
            assert ix < 100, "can't convert " + repr(self) + " to a string"

        if isinstance(x, FORAValue):
            stringVal = x.implVal_.getPythonString()
            if stringVal is None:
                #it's an unloaded string
                x = str(x)
            else:
                x = stringVal
        elif not isinstance(x, str):
            return str(x)

        return x

    def __repr__(self):
        return str(self.implVal_)

    def __coerce__(self, other):
        return None

    def __getstate__(self):
        return (self.implVal_,)

    def __setstate__(self, s):
        self.implVal_ = s[0]

    def type(self):
        """return the Type object of a FORAValue"""
        return FORAValue(self.implVal_.type)

    def toPythonObject(self):
        """Find the best equivalent python object held within this FORAValue.

        In particular, convert any FORAValue which is itself a PythonObject, a
        string, a tuple, a float, or an int"""

        implval = self.implVal_
        assert isinstance(implval, ForaNative.ImplValContainer)

        if implval.isTuple():
            names = implval.getTupleNames()
            for n in names:
                if n is not None:
                    return FORATuple(implval)
            return tuple([FORAValue(x).toPythonObject() for x in implval.getTuple()])

        if implval.isVector():
            return FORAVector(implval)

        if implval.isMutableVector():
            return FORAMutableVector(implval)

        if cmp(implval.type, ForaNative.Nothing) == 0:
            return None

        if cmp(implval.type, ForaNative.UInt1) == 0:
            return implval.pyval

        if cmp(implval.type, ForaNative.Int64) == 0:
            return implval.pyval

        if cmp(implval.type, ForaNative.Float64) == 0:
            return implval.pyval

        if cmp(implval.type, ForaNative.String) == 0:
            return implval.pyval

        return FORAValue(implval)

    @staticmethod
    def makeSymbol(symbolString):
        """return a FORAValue containing a symbol"""
        return FORAValue(ForaNative.makeSymbol(symbolString))

FORAValue.MutableVector = FORAValue.makeSymbol("MutableVector")
FORAValue.Vector = FORAValue.makeSymbol("Vector")
FORAValue.Type = FORAValue.makeSymbol("TypeJOV")
FORAValue.symbol_GetItem = FORAValue.makeSymbol("GetItem")
FORAValue.symbol_SetItem = FORAValue.makeSymbol("SetItem")
FORAValue.symbol_SetItemNoconvert = FORAValue.makeSymbol("SetItemNoconvert")
FORAValue.symbol_Operator = FORAValue.makeSymbol("Operator")
FORAValue.symbol_Member = FORAValue.makeSymbol("Member")
FORAValue.symbol_Size = FORAValue.makeSymbol("size")
FORAValue.symbol_Call = FORAValue.makeSymbol("Call")
FORAValue.symbol_Next = FORAValue.makeSymbol("Next")
FORAValue.symbol_package = FORAValue.makeSymbol("package")
FORAValue.symbol_ExtractMetadata = FORAValue.makeSymbol("ExtractMetadata")
FORAValue.symbol_ShortRepresentation = FORAValue.makeSymbol("ShortRepresentation")

nothing = FORAValue(ForaNative.nothing)

StackTrace = FORAValue(ForaNative.StackTrace)
String = FORAValue(ForaNative.String)

class FORATuple(FORAValue):
    def __init__(self, implval):
        FORAValue.__init__(self, implval)

    def __getitem__(self, x):
        try:
            return FORAValue(self.implVal_[x]).toPythonObject()
        except:
            raise IndexError()

    names_ = property(lambda self: self.implVal_.getTupleNames())

    @staticmethod
    def isTuple(t):
        return t.implVal_.isTuple()

    @staticmethod
    def getNames(t):
        return t.names_


class FORAVector(FORAValue):
    def __init__(self, implval):
        FORAValue.__init__(self, implval)

    def __getitem__(self, x):
        try:
            value = Evaluator.evaluator().getVDM().extractVectorItem(self.implVal_, x)

            if value is not None:
                return FORAValue(value).toPythonObject()
            else:
                return FORAValue.__getitem__(self, x)
        except:
            raise IndexError()

class FORAMutableVector(FORAValue):
    def __init__(self, implval):
        FORAValue.__init__(self, implval)

    def __getitem__(self, x):
        try:
            return FORAValue(self.implVal_[x]).toPythonObject()
        except:
            raise IndexError()

def extractImplValContainer(foraValue):
    """the preferred way to get the implval out of a ForaValue.FORAValue object"""
    return foraValue.implVal_

class FORAException(Exception):
    """base class for all FORA exceptions"""
    def __init__(self, foraVal = None):
        Exception.__init__(self)
        if foraVal is None:
            self.foraVal = nothing
            self.trace = None
            self.valuesInScope = None
        else:
            if not isinstance(foraVal, tuple) or len(foraVal) != 2:
                assert False, "Improperly formed FORA exception."

            stacktraceAndData = foraVal[1]
            # stacktraceAndData = (stacktrace, values in scope)

            if not isinstance(foraVal[1], tuple):
                stacktraceAndData = stacktraceAndData.toPythonObject()

            if not isinstance(stacktraceAndData, tuple) or len(stacktraceAndData) != 2:
                print stacktraceAndData, type(stacktraceAndData)
                assert False, "Improperly formed FORA exception."

            if not (stacktraceAndData[0].type() == StackTrace):
                assert False, "Improperly formed FORA exception."

            self.foraVal = foraVal[0]
            self.trace = stacktraceAndData[0].implVal_.getStackTrace()  # Python list of codeLocations.
            self.valuesInScope = stacktraceAndData[1]

    def __str__(self):
        exceptionString = str(self.foraVal)
        if len(exceptionString) > 1000:
            exceptionString = exceptionString[:800] + exceptionString[-200:]

        return "FORA Exception: " + exceptionString + (
                    "\n\nTraceback:\n" +
                        ErrorFormatting.formatStacktrace(self.trace, self.valuesInScope)
                    if self.trace is not None
                        else
                    " (<no stacktrace available>)")

    def __cmp__(self, other):
        return TypeAwareComparison.typecmp(self, other,
            lambda self, other : cmp(self.foraVal, other.foraVal))

    def __getinitargs__(self):
        return (self.foraVal, self.trace)


def processComputationResult(res):
    """given a FORA.ComputationResult, return or throw the relevant FORAValue
    object. Attempt to convert it to a python object if possible."""
    if res.isException():
        v = FORAValue(res.asException.exception).toPythonObject()

        if isinstance(v, Exception):
            raise v
        else:
            raise FORAException(v)
    if res.isFailure():
        raise FORAFailure(res.asFailure.error)
    return FORAValue(res.asResult.result).toPythonObject()

def binaryOp_(lhs, rhs, op):
    """given lhs, rhs, and op, which are all FORAValues, evaluate a binary
    operator call"""
    return processComputationResult(
            Evaluator.evaluator().evaluate(
                lhs.implVal_,
                FORAValue.symbol_Operator.implVal_,
                op.implVal_,
                rhs.implVal_
                )
            )

class ForaOperatorSymbols(object):
    #internally used symbols
    plus = FORAValue.makeSymbol("+")
    sub = FORAValue.makeSymbol("-")
    mul = FORAValue.makeSymbol("*")
    div = FORAValue.makeSymbol("/")
    mod = FORAValue.makeSymbol("%")
    pow = FORAValue.makeSymbol("**")
    lshift = FORAValue.makeSymbol("<<")
    rshift = FORAValue.makeSymbol(">>")
    lt = FORAValue.makeSymbol("<")
    gt = FORAValue.makeSymbol(">")
    le = FORAValue.makeSymbol("<=")
    ge = FORAValue.makeSymbol(">=")
    eq = FORAValue.makeSymbol("==")
    ne = FORAValue.makeSymbol("!=")

ForaOperatorLambdas = {
    ForaOperatorSymbols.plus:	(lambda x,y: x+y),
    ForaOperatorSymbols.sub:	(lambda x,y: x-y),
    ForaOperatorSymbols.mul:	(lambda x,y: x*y),
    ForaOperatorSymbols.div:	(lambda x,y: x/y),
    ForaOperatorSymbols.mod:	(lambda x,y: x%y),
    ForaOperatorSymbols.pow:	(lambda x,y: x**y),
    ForaOperatorSymbols.lshift:	(lambda x,y: x<<y),
    ForaOperatorSymbols.rshift:	(lambda x,y: x>>y),
    ForaOperatorSymbols.lt:	(lambda x,y: x<y),
    ForaOperatorSymbols.gt:	(lambda x,y: x>y),
    ForaOperatorSymbols.le:	(lambda x,y: x<=y),
    ForaOperatorSymbols.ge:	(lambda x,y: x>=y),
    ForaOperatorSymbols.eq:	(lambda x,y: x==y),
    ForaOperatorSymbols.ne:	(lambda x,y: x!=y)
    }

